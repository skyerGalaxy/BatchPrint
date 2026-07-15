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

fn spawn_backend() {
    let current_exe = env::current_exe().unwrap_or_default();
    let exe_dir = current_exe.parent().unwrap_or(std::path::Path::new("."));

    let backend_name = if cfg!(target_os = "windows") {
        "backend-x86_64-pc-windows-msvc.exe"
    } else if cfg!(target_os = "macos") {
        "backend-x86_64-apple-darwin"
    } else {
        "backend-x86_64-unknown-linux-gnu"
    };

    let backend_path = exe_dir.join(backend_name);
    append_log(&format!("exe_dir: {:?}", exe_dir));
    append_log(&format!("backend_path: {:?}", backend_path));

    if !backend_path.exists() {
        append_log("ERROR: backend binary not found");
        return;
    }
    append_log("backend binary found, spawning...");

    let mut cmd = Command::new(&backend_path);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NEW_CONSOLE: u32 = 0x00000010;
        cmd.creation_flags(CREATE_NEW_CONSOLE);
    }

    match cmd.spawn() {
        Ok(child) => {
            append_log("backend process spawned successfully");
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
        if let Some(ref mut child) = *proc {
            let _ = child.kill();
        }
        *proc = None;
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
            thread::spawn(spawn_backend);
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
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
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
