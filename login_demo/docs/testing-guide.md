---
service: login_demo
topic: testing
status: current
---

# login_demo 测试指南（作业副本）

## 运行方法

在 login_demo 目录运行 `python -m pytest tests/auth/test_session.py -q`。
Python 环境需要安装 pytest。Windows 可直接使用虚拟环境中的 python.exe 完整路径。

## 已覆盖的行为

- `test_expire_boundary`：到期前有效，恰好到期与到期后无效。
- `test_refresh_extends_ttl`：默认有效期 30 分钟。
- `test_issued_token_expires_at_boundary`：实际签发令牌的到期行为。
- 其余用例覆盖篡改令牌、续期、过期后拒绝续期和未知令牌。

## 尚未实现的行为

课件的 `auth.logout()` 仍抛出 NotImplementedError。本次测试明确检查这一现状，不声称退出登录已经完成。
原课件指南提到了 tests/auth/test_session.py，但附件未提供该文件。本目录测试由本次作业补齐。迁移只改位置，不改断言。
