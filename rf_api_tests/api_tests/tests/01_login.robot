*** Settings ***
Resource    ../common/base.resource
Suite Setup       Ensure Admin Exists
Suite Teardown    Delete API Session

*** Keywords ***
Ensure Admin Exists
    Create API Session
    # 尝试登录，如果失败则创建
    ${body}=    Create Dictionary    username=admin    password=admin123
    ${resp}=    POST API    /login    ${body}
    IF    ${resp.status_code} != 200
        Log To Console    ⚠️ admin 账号不存在，自动创建中...
        ${create_body}=    Create Dictionary
        ...    username=admin
        ...    password=admin123
        ...    role=admin
        ${create_resp}=    POST API    /users    ${create_body}
        Log To Console    创建结果: ${create_resp.status_code}
    END
    Delete API Session