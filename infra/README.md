# Biteagle Infra

Biteagle 项目基础设施配置。

## 服务

| 服务 | 容器名 | 端口 |
|------|--------|------|
| PostgreSQL | biteagle-postgres | 5433 |
| Redis | biteagle-redis | 6380 |
| RabbitMQ | biteagle-rabbitmq | 5672 (AMQP), 15672 (UI) |
| Neo4j | biteagle-neo4j | 7474 (HTTP), 7687 (Bolt) |
| Adminer | biteagle-adminer | 8080 |

## 使用

```bash
# 启动所有服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

## 数据库连接

```
Host: localhost
Port: 5433
User: postgres
Password: postgres
Database: biteagle
```

## Redis 连接

```
Host: localhost
Port: 6380
```

## RabbitMQ 连接

```
AMQP URL: amqp://admin:admin@localhost:5672
Management UI: http://localhost:15672
Username: admin
Password: admin
```

## Neo4j 连接

```
Bolt URL: bolt://localhost:7687
HTTP URL: http://localhost:7474
Username: neo4j
Password: biteagle_password
```
