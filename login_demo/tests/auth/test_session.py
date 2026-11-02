"""新增作业测试；业务源码复用课件，不改变其预期行为。"""
import pytest
from app import auth
from app.session import SESSION_TTL_SECONDS, is_session_valid, refresh_expiry

@pytest.mark.parametrize('now,expected', [(99, True), (100, False), (101, False)])
def test_expire_boundary(now, expected):
    assert is_session_valid(now, 100) is expected

def test_refresh_extends_ttl():
    assert SESSION_TTL_SECONDS == 30 * 60
    assert refresh_expiry(100) == 1900

def test_issued_token_expires_at_boundary():
    token = auth.issue_token('alice', now=100)
    assert auth.expire_at(token) == 1900
    assert auth.check(token, now=1899)
    assert not auth.check(token, now=1900)
    assert not auth.check(token, now=1901)

def test_tampered_token_is_rejected():
    token = auth.issue_token('alice', now=100)
    assert not auth.check(token + 'x', now=101)

def test_touch_live_token():
    token = auth.issue_token('alice', now=100)
    assert auth.touch(token, now=200) == 2000
    assert auth.check(token, now=1999)

def test_touch_expired_token_is_rejected():
    token = auth.issue_token('alice', now=100)
    assert auth.touch(token, now=1900) is None

def test_unknown_token_is_rejected():
    assert not auth.check('missing', now=100)
    assert auth.expire_at('missing') is None

def test_logout_is_still_unimplemented():
    with pytest.raises(NotImplementedError):
        auth.logout('unused')
