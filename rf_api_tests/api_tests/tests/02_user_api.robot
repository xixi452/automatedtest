*** Settings ***
Resource    ../common/base.resource
Suite Setup       Create API Session
Suite Teardown    Run Keywords    Delete Test User    AND    Delete API Session

*** Variables ***
${TEST_USERNAME}    rf_test_user
${TEST_PASSWORD}    Test@123456
&{VALID_ROLES}      admin=user=merchant=supplier

*** Keywords ***
Delete Test User
    [Documentation]    清理测试数据：按用户名查找并删除
    ${resp}=    GET API    /users
    ${json}=    To Json    ${resp.content}
    FOR    ${item}    IN    @{json}[data]
        IF    '${item}[username]' == '${TEST_USERNAME}'
            DELETE API    /users/${item}[id]
            BREAK
        END
    END

*** Test Cases ***
TC_USER_01_新增用户_成功
    ${body}=    Create Dictionary
    ...    username=${TEST_USERNAME}
    ...    password=${TEST_PASSWORD}
    ...    role=merchant
    ${resp}=    POST API    /users    ${body}
    Should Be HTTP Status    ${resp}    201
    Should Be Code           ${resp}    201
    ${data}=    Get Response Data    ${resp}
    Set Suite Variable       ${CREATED_USER_ID}    ${data}[id]
    Should Be Equal          ${data}[role]    merchant

TC_USER_02_查询用户列表_包含新增用户
    ${resp}=    GET API    /users
    Should Be Code    ${resp}    200
    ${data}=    Get Response Data    ${resp}
    ${found}=    Evaluate    any(u['username']=='${TEST_USERNAME}' for u in $data)
    Should Be True    ${found}

TC_USER_03_编辑用户角色
    ${body}=    Create Dictionary    role=supplier
    ${resp}=    PUT API    /users/${CREATED_USER_ID}    ${body}
    Should Be Code    ${resp}    200
    ${data}=    Get Response Data    ${resp}
    Should Be Equal    ${data}[role]    supplier

TC_USER_04_非法角色_创建失败
    ${body}=    Create Dictionary
    ...    username=bad_role_user
    ...    password=${TEST_PASSWORD}
    ...    role=hacker
    ${resp}=    POST API    /users    ${body}
    Should Be HTTP Status    ${resp}    400
    Should Be Code           ${resp}    400

TC_USER_05_缺少必填字段_创建失败
    ${body}=    Create Dictionary    username=no_pwd_user
    ${resp}=    POST API    /users    ${body}
    Should Be HTTP Status    ${resp}    400

TC_USER_06_删除用户_成功
    ${resp}=    DELETE API    /users/${CREATED_USER_ID}
    Should Be Code    ${resp}    200
    # 验证删除后查不到
    ${resp2}=    GET API    /users/${CREATED_USER_ID}
    Should Be HTTP Status    ${resp2}    404