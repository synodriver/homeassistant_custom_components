# Home Assistant 青萍空气检测仪自定义组件

## 项目简介

这是一个 Home Assistant 自定义组件，用于集成青萍科技（QingPing）的 IoT 空气检测设备。该组件允许用户通过 Home Assistant 监控和管理青萍空气检测仪的各种传感器数据。

## 功能特性

### 支持的传感器类型
- **温度** (temperature) - 摄氏度 (°C)
- **湿度** (humidity) - 百分比 (%)
- **大气压力** (pressure) - 千帕 (kPa)
- **电池电量** (battery) - 百分比 (%)
- **TVOC** (总挥发性有机化合物) - 微克/立方米 (μg/m³)
- **CO2** (二氧化碳) - 百万分率 (ppm)
- **PM2.5** (细颗粒物) - 微克/立方米 (μg/m³)

### 主要功能
- 通过青萍开放 API 获取设备数据
- 支持多设备管理
- 自动设备发现和配置
- 实时数据更新（1分钟间隔）
- 友好的用户界面配置流程

## 项目结构

```
custom_components/qingpingiot/
├── __init__.py          # 主组件初始化
├── config_flow.py       # 配置流程管理
├── consts.py           # 常量定义
├── sensor.py           # 传感器实体实现
├── manifest.json       # 组件清单文件
├── icon.png            # 组件图标
└── icons.json          # 图标配置
```

## 核心文件说明

### `manifest.json`
组件清单文件，定义了：
- 组件域名：`qingpingiot`
- 版本：`0.0.1`
- 依赖：`qingping_sdk`
- 集成类型：`hub`（云轮询）
- 配置流程：支持

### `__init__.py`
主要功能：
- 组件生命周期管理
- 青萍 SDK 客户端初始化
- 平台设置和卸载
- 配置更新监听

### `config_flow.py`
配置流程管理：
- 用户输入 APP_KEY 和 APP_SECRET
- API 连接验证
- 配置项创建和更新
- 重新认证支持

### `sensor.py`
传感器实体实现：
- 支持 7 种传感器类型
- 设备信息管理
- 历史数据获取
- 状态更新和错误处理

### `consts.py`
常量定义：
- 域名：`qingpingiot`
- 配置键：`app_key`, `app_secret`
- 青萍官网 URL

## 技术特点

1. **异步设计**：全面使用 async/await 模式，提高性能
2. **错误处理**：完善的异常处理和认证失败重试机制
3. **设备管理**：自动发现设备并创建对应的传感器实体
4. **数据同步**：定期从青萍云端获取最新传感器数据
5. **用户体验**：提供直观的配置界面和设备信息展示

## 安装和配置

1. 将 `custom_components/qingpingiot` 文件夹复制到 Home Assistant 的 `custom_components` 目录
2. 重启 Home Assistant
3. 在集成页面添加"青萍 IoT"集成
4. 输入从青萍开发者平台获取的 APP_KEY 和 APP_SECRET
5. 完成配置后，组件会自动发现并添加所有支持的传感器

## 依赖项

- `qingping_sdk`：青萍官方 Python SDK
- Home Assistant 核心组件

## 作者信息

- 作者：synodriver
- 邮箱：diguohuangjiajinweijun@gmail.com
- GitHub：https://github.com/synodriver/homeassistant_custom_components

## 版本历史

- v0.0.1：初始版本
  - 支持基本传感器数据读取
  - 实现配置流程
  - 添加设备管理功能

## 许可证

Copyright (c) 2008-2024 synodriver

## 注意事项

- 需要在青萍开发者平台注册并获取 API 密钥
- 组件主要支持青萍的"商用"设备，这些设备无法直接接入米家等平台
- 数据更新频率为 1 分钟，可根据需要调整
- 如遇到问题，请查看 Home Assistant 日志或访问项目 GitHub 页面反馈