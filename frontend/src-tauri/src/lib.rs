use fs_extra::dir::{move_dir, CopyOptions};
use std::fs;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Command, Child};
use std::sync::Mutex;
use std::env;
use std::time::Duration;
use std::thread;
use tauri::Manager;

static BACKEND_PROCESS: Mutex<Option<Child>> = Mutex::new(None);
static BACKEND_READY: Mutex<bool> = Mutex::new(false);
static BACKEND_LOG: Mutex<String> = Mutex::new(String::new());

#[tauri::command]
fn get_backend_status() -> String {
    let ready = *BACKEND_READY.lock().unwrap();
    let log = BACKEND_LOG.lock().unwrap().clone();
    if ready {
        format!("ready\n{}", log)
    } else {
        format!("pending\n{}", log)
    }
}

fn append_log(msg: &str) {
    if let Ok(mut log) = BACKEND_LOG.lock() {
        log.push_str(msg);
        log.push('\n');
    }
}

fn port_8000_in_use() -> bool {
    TcpStream::connect_timeout(
        &"127.0.0.1:8000".parse().unwrap(),
        Duration::from_millis(300),
    )
    .is_ok()
}

fn kill_stale_backend(dest_name: &str, dest_path: &PathBuf) {
    if !port_8000_in_use() {
        return;
    }
    append_log("port 8000 already in use, killing stale backend processes...");

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        let _ = Command::new("taskkill")
            .args(["/F", "/T", "/IM", dest_name])
            .creation_flags(CREATE_NO_WINDOW)
            .status();
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = dest_name;
        let _ = Command::new("pkill")
            .args(["-f", &dest_path.to_string_lossy().to_string()])
            .status();
    }

    for _ in 0..10 {
        if !port_8000_in_use() {
            append_log("stale backend killed, port 8000 released");
            return;
        }
        thread::sleep(Duration::from_millis(300));
    }
    append_log("WARNING: port 8000 still in use (occupied by another program?)");
    #[cfg(target_os = "windows")]
    let _ = dest_path;
}

fn prepare_and_spawn_backend(app_data_dir: PathBuf, resource_dir: PathBuf) {
    let src_name = if cfg!(target_os = "windows") {
        "backend-x86_64-pc-windows-msvc.exe"
    } else if cfg!(target_os = "macos") {
        "backend-x86_64-apple-darwin"
    } else {
        "backend-x86_64-unknown-linux-gnu"
    };

    let dest_name = if cfg!(target_os = "windows") {
        "backend.exe"
    } else {
        "backend"
    };

    let src_path = resource_dir.join("binaries").join(src_name);
    let dest_path = app_data_dir.join(dest_name);

    append_log(&format!("resource_dir: {:?}", resource_dir));
    append_log(&format!("app_data_dir: {:?}", app_data_dir));
    append_log(&format!("src_path: {:?}", src_path));
    append_log(&format!("dest_path: {:?}", dest_path));

    // 残留的旧后端会占用 8000 端口并锁定 dest 文件，先清理
    kill_stale_backend(dest_name, &dest_path);

    if src_path.exists() {
        let need_copy = match dest_path.metadata() {
            Ok(dest_meta) => {
                match src_path.metadata() {
                    Ok(src_meta) => {
                        src_meta.modified().ok() != dest_meta.modified().ok()
                    }
                    Err(_) => false,
                }
            }
            Err(_) => true,
        };

        if need_copy {
            append_log("copying backend from resources to app data...");
            match fs::copy(&src_path, &dest_path) {
                Ok(_) => append_log("copy succeeded"),
                Err(e) => append_log(&format!("copy failed: {}", e)),
            }
        } else {
            append_log("backend already up to date in app data");
        }
    } else {
        append_log("WARNING: backend not found in resources");
    }

    if !dest_path.exists() {
        append_log("ERROR: backend binary not available");
        return;
    }

    #[cfg(not(target_os = "windows"))]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = fs::set_permissions(&dest_path, fs::Permissions::from_mode(0o755));
    }

    append_log("spawning backend...");
    let mut cmd = Command::new(&dest_path);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    match cmd.spawn() {
        Ok(child) => {
            append_log("backend process spawned");
            let mut proc = BACKEND_PROCESS.lock().unwrap();
            *proc = Some(child);

            for i in 0..60 {
                thread::sleep(Duration::from_millis(500));
                if check_backend_health() {
                    append_log(&format!("backend ready after {} checks", i + 1));
                    let mut ready = BACKEND_READY.lock().unwrap();
                    *ready = true;
                    return;
                }
            }
            append_log("WARNING: backend health check timed out (30s)");
        }
        Err(e) => {
            append_log(&format!("ERROR: spawn failed: {}", e));
        }
    }
}

fn check_backend_health() -> bool {
    match TcpStream::connect_timeout(
        &"127.0.0.1:8000".parse().unwrap(),
        Duration::from_millis(500),
    ) {
        Ok(mut stream) => {
            let _ = stream.set_read_timeout(Some(Duration::from_secs(1)));
            let _ = stream.set_write_timeout(Some(Duration::from_secs(1)));
            let request = b"GET /health HTTP/1.1\r\nHost: localhost:8000\r\nConnection: close\r\n\r\n";
            if stream.write_all(request).is_ok() {
                let mut response = String::new();
                if stream.read_to_string(&mut response).is_ok() {
                    return response.contains("200") || response.contains("ok");
                }
            }
            false
        }
        Err(_) => false,
    }
}

fn stop_backend() {
    if let Ok(mut proc) = BACKEND_PROCESS.lock() {
        if let Some(mut child) = proc.take() {
            // PyInstaller onefile 的 exe 会派生子进程，必须杀掉整个进程树
            #[cfg(target_os = "windows")]
            {
                use std::os::windows::process::CommandExt;
                const CREATE_NO_WINDOW: u32 = 0x08000000;
                let _ = Command::new("taskkill")
                    .args(["/F", "/T", "/PID", &child.id().to_string()])
                    .creation_flags(CREATE_NO_WINDOW)
                    .status();
            }
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            let app_data_dir = app.handle().path().app_data_dir()
                .unwrap_or_else(|_| PathBuf::from("."));
            let resource_dir = app.handle().path().resource_dir()
                .unwrap_or_else(|_| PathBuf::from("."));
            thread::spawn(move || prepare_and_spawn_backend(app_data_dir, resource_dir));
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if window.label() == "main" {
                    stop_backend();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            move_folder_with_extra,
            open_folder,
            get_backend_status
        ])
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|_app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                stop_backend();
            }
        });
}

#[tauri::command]
async fn move_folder_with_extra(src: String, dest: String) -> Result<String, String> {
    let src = src.trim().to_string();
    let dest = dest.trim().to_string();

    if src.is_empty() || dest.is_empty() {
        return Err("源或目标路径为空".into());
    }

    let src_path = PathBuf::from(&src);
    let dest_path = PathBuf::from(&dest);

    if !src_path.exists() {
        return Err(format!("源路径不存在: {}", src));
    }

    if src_path == dest_path {
        return Ok("选择的路径与当前路径相同，未执行移动".into());
    }

    let src_real = src_path
        .canonicalize()
        .map_err(|e| format!("源路径解析失败: {}", e))?;

    let dest_real_opt = dest_path.canonicalize().ok();
    if let Some(dest_real) = &dest_real_opt {
        if dest_real.starts_with(&src_real) {
            return Err("目标路径位于源目录内，无法移动".into());
        }
    }

    if !dest_path.exists() {
        fs::create_dir_all(&dest_path)
            .map_err(|e| format!("创建目标目录失败: {}", e))?;
    }

    let mut options = CopyOptions::new();
    options.overwrite = true;
    options.copy_inside = false;

    match fs::read_dir(&src_real) {
        Ok(entries) => {
            for entry in entries {
                if let Ok(entry) = entry {
                    let src_item = entry.path();
                    let item_name = entry.file_name();
                    let dest_item = dest_path.join(&item_name);

                    if dest_item.exists() {
                        if dest_item.is_dir() {
                            fs::remove_dir_all(&dest_item)
                                .map_err(|e| format!("删除目标目录失败: {}", e))?;
                        } else {
                            fs::remove_file(&dest_item)
                                .map_err(|e| format!("删除目标文件失败: {}", e))?;
                        }
                    }

                    if src_item.is_dir() {
                        move_dir(&src_item, &dest_item, &options)
                            .map_err(|e| format!("移动目录 {:?} 失败: {:?}", item_name, e))?;
                    } else {
                        fs::rename(&src_item, &dest_item)
                            .map_err(|e| format!("移动文件 {:?} 失败: {}", item_name, e))?;
                    }
                }
            }

            fs::remove_dir(&src_real)
                .map_err(|e| format!("删除源目录失败: {}", e))?;

            Ok(format!("成功将 {} 的内容移动到 {}", src, dest))
        },
        Err(e) => Err(format!("读取源目录失败: {}", e)),
    }
}

#[tauri::command]
fn open_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("explorer")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("打开文件夹失败: {}", e))?;
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("打开文件夹失败: {}", e))?;
    }
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("打开文件夹失败: {}", e))?;
    }
    Ok(())
}
