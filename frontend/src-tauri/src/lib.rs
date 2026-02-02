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
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            move_folder_with_extra
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}


use fs_extra::dir::{move_dir, CopyOptions};
use std::fs;
use std::path::{PathBuf};

#[tauri::command]
async fn move_folder_with_extra(src: String, dest: String) -> Result<String, String> {
    // 基本清理与校验
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

    // 规范化路径，防止目标位于源内部等危险情况
    let src_real = src_path
        .canonicalize()
        .map_err(|e| format!("源路径解析失败: {}", e))?;

    // 目标可能不存在，canonicalize 可能失败；这里先尝试，失败不致命
    let dest_real_opt = dest_path.canonicalize().ok();
    if let Some(dest_real) = &dest_real_opt {
        if dest_real.starts_with(&src_real) {
            return Err("目标路径位于源目录内，无法移动".into());
        }
    }

    // 确保目标目录存在
    if !dest_path.exists() {
        fs::create_dir_all(&dest_path)
            .map_err(|e| format!("创建目标目录失败: {}", e))?;
    }

    // 配置拷贝/移动选项
    let mut options = CopyOptions::new();
    options.overwrite = true;   // 覆盖已有文件
    options.copy_inside = false; // 移动源目录的内容到目标目录，而不是把源目录本身移动进去

    // 手动处理：遍历源目录的每个子目录/文件，逐个移动到目标目录
    match fs::read_dir(&src_real) {
        Ok(entries) => {
            for entry in entries {
                if let Ok(entry) = entry {
                    let src_item = entry.path();
                    let item_name = entry.file_name();
                    let dest_item = dest_path.join(&item_name);
                    
                    // 如果目标已存在，先删除
                    if dest_item.exists() {
                        if dest_item.is_dir() {
                            fs::remove_dir_all(&dest_item)
                                .map_err(|e| format!("删除目标目录失败: {}", e))?;
                        } else {
                            fs::remove_file(&dest_item)
                                .map_err(|e| format!("删除目标文件失败: {}", e))?;
                        }
                    }
                    
                    // 移动或复制到目标
                    if src_item.is_dir() {
                        move_dir(&src_item, &dest_item, &options)
                            .map_err(|e| format!("移动目录 {:?} 失败: {:?}", item_name, e))?;
                    } else {
                        fs::rename(&src_item, &dest_item)
                            .map_err(|e| format!("移动文件 {:?} 失败: {}", item_name, e))?;
                    }
                }
            }
            
            // 所有内容移动完毕后，删除空的源目录
            fs::remove_dir(&src_real)
                .map_err(|e| format!("删除源目录失败: {}", e))?;
            
            Ok(format!("成功将 {} 的内容移动到 {}", src, dest))
        },
        Err(e) => Err(format!("读取源目录失败: {}", e)),
    }
}

// 别忘了在 generate_handler 中注册这个命令