*** Settings ***
Library    RequestsLibrary
Library    Collections

*** Variables ***
${BASE_URL}       http://localhost:8081
${API_PREFIX}     /api

*** Keywords ***
Create API Session
    Create Session    api    ${BASE_URL}    verify=${FALSE}

Delete API Session
    Delete All Sessions

# ========== 通用请求封装 (关键：添加 expected_status=ANY) ==========
GET API
    [Arguments]    ${endpoint}    ${params}=${EMPTY}
    # ✅ 修复1: expected_status=ANY 阻止库自动对4xx/5xx抛异常
    ${resp}=    GET On Session    api    ${API_PREFIX}${endpoint}    params=${params}    expected_status=ANY
    RETURN    ${resp}

POST API
    [Arguments]    ${endpoint}    ${body}
    ${resp}=    POST On Session    api    ${API_PREFIX}${endpoint}    json=${body}    expected_status=ANY
    RETURN    ${resp}

PUT API
    [Arguments]    ${endpoint}    ${body}
    ${resp}=    PUT On Session    api    ${API_PREFIX}${endpoint}    json=${body}    expected_status=ANY
    RETURN    ${resp}

DELETE API
    [Arguments]    ${endpoint}
    ${resp}=    DELETE On Session    api    ${API_PREFIX}${endpoint}    expected_status=ANY
    RETURN    ${resp}

# ========== 通用断言 (关键：兼容无 message 字段的响应) ==========
Should Be HTTP Status
    [Arguments]    ${response}    ${expected_status}
    Should Be Equal As Integers    ${response.status_code}    ${expected_status}
    ...    msg=期望 HTTP ${expected_status}, 实际 HTTP ${response.status_code} | Body: ${response.text}

Should Be Code
    [Arguments]    ${response}    ${expected_code}
    # ✅ 修复2: 使用 .json() 替代废弃的 To Json
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal As Integers    ${json}[code]    ${expected_code}
    ...    msg=期望 code=${expected_code}, 实际 code=${json}[code] | Body: ${response.text}

Get Response Data
    [Arguments]    ${response}
    ${json}=    Set Variable    ${response.json()}
    RETURN    ${json}[data]