*** Settings ***
Resource    ../common/base.resource
Suite Setup       Create API Session
Suite Teardown    Run Keywords    Cleanup Test Medicine    AND    Delete API Session

*** Variables ***
${TEST_MED_NAME}       RF测试药品
${TEST_BATCH_NO}       BATCH-RF-001
${TEST_EXPIRY_DATE}    2027-12-31

*** Keywords ***
Cleanup Test Medicine
    ${resp}=    GET API    /medicines
    ${json}=    To Json    ${resp.content}
    FOR    ${item}    IN    @{json}[data]
        IF    '${item}[name]' == '${TEST_MED_NAME}'
            DELETE API    /medicines/${item}[id]
            BREAK
        END
    END

*** Test Cases ***
TC_MED_01_新增药品_成功
    ${body}=    Create Dictionary
    ...    name=${TEST_MED_NAME}
    ...    batch_no=${TEST_BATCH_NO}
    ...    expiry_date=${TEST_EXPIRY_DATE}
    ...    price=25.50
    ...    stock=200
    ...    manufacturer=测试制药有限公司
    ${resp}=    POST API    /medicines    ${body}
    Should Be HTTP Status    ${resp}    201
    ${data}=    Get Response Data    ${resp}
    Set Suite Variable       ${MED_ID}    ${data}[id]
    Should Be Equal    ${data}[batch_no]     ${TEST_BATCH_NO}
    Should Be Equal    ${data}[expiry_date]  ${TEST_EXPIRY_DATE}

TC_MED_02_有效期格式错误_创建失败
    ${body}=    Create Dictionary
    ...    name=格式错误药品
    ...    batch_no=BATCH-ERR
    ...    expiry_date=2027/12/31
    ...    price=10
    ${resp}=    POST API    /medicines    ${body}
    Should Be HTTP Status    ${resp}    400

TC_MED_03_编辑药品厂商
    ${body}=    Create Dictionary    manufacturer=更新制药集团
    ${resp}=    PUT API    /medicines/${MED_ID}    ${body}
    Should Be Code    ${resp}    200
    ${data}=    Get Response Data    ${resp}
    Should Be Equal    ${data}[manufacturer]    更新制药集团

TC_MED_04_缺少批号_创建失败
    ${body}=    Create Dictionary
    ...    name=无批号药品
    ...    expiry_date=2027-06-01
    ...    price=15
    ${resp}=    POST API    /medicines    ${body}
    Should Be HTTP Status    ${resp}    400

TC_MED_05_删除药品_成功
    ${resp}=    DELETE API    /medicines/${MED_ID}
    Should Be Code    ${resp}    200
    ${resp2}=    GET API    /medicines/${MED_ID}
    Should Be HTTP Status    ${resp2}    404