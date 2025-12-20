use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
struct AppConfig {
    image_storage_path: String,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            image_storage_path: String::from("/user/images"),
        }
    }
}

#[tauri::command]
fn save_config(config_path: String, image_path: String) -> Result<String, String> {
    let config = AppConfig {
        image_storage_path: image_path.clone(),
    };
    
    let config_json = serde_json::to_string_pretty(&config)
        .map_err(|e| format!("序列化配置失败: {}", e))?;
    
    fs::write(&config_path, config_json)
        .map_err(|e| format!("保存配置文件失败: {}", e))?;
    
    Ok(image_path)
}

#[tauri::command]
fn load_config(config_path: String) -> Result<AppConfig, String> {
    match fs::read_to_string(&config_path) {
        Ok(content) => {
            serde_json::from_str(&content)
                .map_err(|e| format!("解析配置文件失败: {}", e))
        }
        Err(_) => {
            // 如果配置文件不存在，返回默认配置
            Ok(AppConfig::default())
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .invoke_handler(tauri::generate_handler![save_config, load_config])
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
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
