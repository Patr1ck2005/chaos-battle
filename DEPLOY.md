# Chaos Battle 云服务器部署

下面是最简单的部署方式，不考虑 HTTPS、反向代理和安全加固。

## 1. 准备服务器

使用一台 Linux 云服务器，例如 Ubuntu 22.04。

开放端口：

```bash
8080
```

## 2. 安装 Python

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

## 3. 上传项目

方式一：用 git 拉取项目。

```bash
git clone <你的项目仓库地址> chaos_battle
cd chaos_battle
```

方式二：直接把本地 `chaos_battle` 文件夹上传到服务器，然后进入目录。

```bash
cd chaos_battle
```

## 4. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. 启动游戏

```bash
python run.py
```

看到类似输出后即可访问：

```text
Chaos Battle server running at http://0.0.0.0:8080
```

浏览器打开：

```text
http://服务器公网IP:8080/
```

## 6. 后台运行

最简单可以用 `nohup`：

```bash
source .venv/bin/activate
nohup python run.py > server.log 2>&1 &
```

查看日志：

```bash
tail -f server.log
```

停止服务：

```bash
pkill -f "python run.py"
```

## 7. 更新代码

如果是 git 部署：

```bash
cd chaos_battle
git pull
source .venv/bin/activate
pkill -f "python run.py"
nohup python run.py > server.log 2>&1 &
```
