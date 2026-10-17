# Chaos Battle — fork

**[Aurora-b1t/chaos_battle](https://github.com/Aurora-b1t/chaos_battle) 的保留分支。** 浏览器客户端与 Python aiohttp 服务端实现小型多人战斗游戏。

[English](README.md) · [上游](https://github.com/Aurora-b1t/chaos_battle) · [部署旧说明](DEPLOY.md) · [历史](docs/README-history.md)

## 来源与差异

原游戏与架构归属上游及其贡献者。**2026-10-17** 核对时，本 fork 的公开 `master`（`3edd102`）相对上游 `master`（`2a9bea6`）为 **0 个独有提交、落后 1 个提交**。因此不声称独立实现或存在已验证的专属功能。[固定版本对照](https://github.com/Aurora-b1t/chaos_battle/compare/2a9bea6ed43a8738a916b2c5d919ceeb71b1092f...Patr1ck2005:3edd1029c08661666d23189c27e12be1792b4234)。

## 源码与本机运行

| 路径 | 职责 |
|---|---|
| [client/](client/) | 浏览器界面、客户端和已有精灵图 |
| [server/](server/) | Python 游戏、房间与网络实现 |
| [run.py](run.py) | 服务端入口 |
| [requirements.txt](requirements.txt) | aiohttp 依赖 |

历史源码入口：

```bash
python -m pip install -r requirements.txt
python run.py
```

文档地址为 `http://127.0.0.1:8080/`；服务器可能监听所有网卡，共享网络运行前应先核对配置。[DEPLOY.md](DEPLOY.md) 是旧的最小部署说明，不代表生产加固或目前在线服务。

## 状态与许可

上游衍生历史快照。本次未新拍截图、部署或验收多人对局；公开基线之外的本机改动不写成已发布功能。

检查的公开快照没有仓库整体开源许可证。保留上游归属，复用条件向相应权利人确认，本次不新增 MIT 许可。
