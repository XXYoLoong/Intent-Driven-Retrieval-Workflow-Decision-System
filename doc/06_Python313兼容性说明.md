# Python 3.13 兼容性说明

## 一、依赖冲突解决方案

### 问题描述

在使用 Python 3.13 安装依赖时，可能会遇到以下依赖冲突：

```
ERROR: opentelemetry-exporter-otlp-proto-common 1.35.0 requires opentelemetry-proto==1.35.0, 
but you have opentelemetry-proto 1.15.0 which is incompatible.
```

### 解决方案

#### 方案 1: 使用修复后的 requirements.txt（推荐）

已更新 `requirements.txt`，固定了 OpenTelemetry 相关包的版本范围，避免冲突：

```txt
opentelemetry-api>=1.21.0,<2.0.0
opentelemetry-sdk>=1.21.0,<2.0.0
opentelemetry-instrumentation-fastapi>=0.42b0,<1.0.0
opentelemetry-exporter-jaeger>=1.21.0,<2.0.0
opentelemetry-proto>=1.15.0,<2.0.0
```

#### 方案 2: 手动安装兼容版本

如果仍有冲突，可以手动指定版本：

```bash
pip install opentelemetry-proto==1.15.0 --force-reinstall
pip install -r requirements.txt
```

#### 方案 3: 忽略可选依赖（如果不需要 Jaeger）

如果不需要 Jaeger 追踪功能，可以注释掉相关依赖：

```txt
# Observability (可选)
# opentelemetry-api>=1.21.0
# opentelemetry-sdk>=1.21.0
# opentelemetry-instrumentation-fastapi>=0.42b0
# opentelemetry-exporter-jaeger>=1.21.0
```

## 二、Python 3.13 特定注意事项

### 1. 虚拟环境创建

Python 3.13 可能需要明确指定版本：

```bash
# Windows
py -3.13 -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3.13 -m venv .venv
source .venv/bin/activate
```

### 2. 依赖安装

使用 `python -m pip` 而不是直接使用 `pip`：

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 已知兼容性问题

#### ChromaDB

ChromaDB 在 Python 3.13 上可能需要额外依赖：

```bash
# 如果 ChromaDB 安装失败，尝试：
pip install chromadb --no-cache-dir
```

#### psycopg2-binary

如果 `psycopg2-binary` 安装失败，可以尝试：

```bash
# 先安装构建工具
pip install setuptools wheel

# 再安装 psycopg2-binary
pip install psycopg2-binary
```

### 4. 验证安装

安装完成后，验证关键包：

```bash
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import sqlalchemy; print(f'SQLAlchemy: {sqlalchemy.__version__}')"
python -c "import chromadb; print('ChromaDB: OK')"
python -c "import openai; print('OpenAI: OK')"
```

## 三、完整安装步骤（Python 3.13）

### 1. 创建虚拟环境

```bash
# Windows
py -3.13 -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3.13 -m venv .venv
source .venv/bin/activate
```

### 2. 升级 pip

```bash
python -m pip install --upgrade pip setuptools wheel
```

### 3. 安装依赖（分步安装，便于排查）

```bash
# 核心依赖
python -m pip install fastapi uvicorn pydantic pydantic-settings

# 数据库
python -m pip install sqlalchemy alembic psycopg2-binary asyncpg

# 向量存储
python -m pip install chromadb

# LLM
python -m pip install openai

# 可观测性（如果遇到冲突，可以跳过）
python -m pip install opentelemetry-api opentelemetry-sdk opentelemetry-proto==1.15.0
python -m pip install opentelemetry-instrumentation-fastapi opentelemetry-exporter-jaeger

# 其他工具
python -m pip install python-dotenv pyyaml structlog

# 测试工具
python -m pip install pytest pytest-asyncio pytest-cov

# 开发工具
python -m pip install black ruff mypy
```

### 4. 或者使用 requirements.txt（推荐）

```bash
python -m pip install -r requirements.txt
```

如果遇到冲突，可以忽略警告继续：

```bash
python -m pip install -r requirements.txt --no-deps
python -m pip install opentelemetry-proto==1.15.0
python -m pip install -r requirements.txt
```

## 四、故障排查

### 问题 1: OpenTelemetry 版本冲突

**症状**: 
```
ERROR: opentelemetry-exporter-otlp-proto-common requires opentelemetry-proto==1.35.0
```

**解决**:
```bash
# 强制安装兼容版本
pip install opentelemetry-proto==1.15.0 --force-reinstall --no-deps
pip install opentelemetry-exporter-jaeger --no-deps
```

### 问题 2: ChromaDB 安装失败

**症状**: 
```
ERROR: Failed building wheel for chromadb
```

**解决**:
```bash
# 安装构建工具
pip install setuptools wheel cmake

# 使用预编译版本
pip install chromadb --only-binary :all:
```

### 问题 3: psycopg2-binary 安装失败

**症状**: 
```
ERROR: Failed building wheel for psycopg2-binary
```

**解决**:
```bash
# Windows: 可能需要 Visual C++ Build Tools
# Linux: 安装 PostgreSQL 开发库
sudo apt-get install libpq-dev python3-dev

# 然后重试
pip install psycopg2-binary
```

## 五、最小化安装（如果遇到大量冲突）

如果遇到大量依赖冲突，可以尝试最小化安装，只安装核心功能：

```bash
# 最小化 requirements.txt
cat > requirements-minimal.txt << EOF
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
sqlalchemy>=2.0.23
alembic>=1.12.1
psycopg2-binary>=2.9.9
chromadb>=0.4.18
openai>=1.3.0
python-dotenv>=1.0.0
pyyaml>=6.0.1
structlog>=23.2.0
EOF

pip install -r requirements-minimal.txt
```

注意：最小化安装会缺少可观测性功能（Jaeger 追踪），但核心功能可用。

## 六、验证安装成功

运行以下命令验证：

```bash
# 检查 Python 版本
python --version  # 应该是 3.13.x

# 检查关键包
python -c "import sys; print(f'Python: {sys.version}')"
python -c "import fastapi; print('FastAPI: OK')"
python -c "import sqlalchemy; print('SQLAlchemy: OK')"
python -c "import chromadb; print('ChromaDB: OK')"
python -c "import openai; print('OpenAI: OK')"

# 尝试启动服务（会检查更多依赖）
python run.py
```

## 七、推荐配置

对于 Python 3.13，推荐使用：

1. **虚拟环境**: 使用 `.venv` 而不是 `venv`（避免路径问题）
2. **pip 版本**: 使用最新版本的 pip
3. **依赖管理**: 使用 `python -m pip` 而不是直接 `pip`

## 八、后续更新

如果 Python 3.13 的兼容性问题在后续版本中得到解决，可以：

1. 更新 `requirements.txt` 中的版本约束
2. 移除版本上限（`<2.0.0`）
3. 使用最新的兼容版本

## 九、获取帮助

如果仍然遇到问题：

1. 查看完整错误日志
2. 检查 Python 版本: `python --version`
3. 检查 pip 版本: `pip --version`
4. 尝试清理后重新安装:
   ```bash
   pip uninstall -y -r requirements.txt
   pip cache purge
   pip install -r requirements.txt
   ```
