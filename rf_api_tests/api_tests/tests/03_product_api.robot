*** Settings ***
Resource    ../common/base.resource
Suite Setup       Create API Session
Suite Teardown    Run Keywords    Cleanup Test Product    AND    Delete API Session

*** Variables ***
${TEST_PRODUCT_NAME}    RF测试商品

*** Keywords ***
Cleanup Test Product
    ${resp}=    GET API    /products
    ${json}=    To Json    ${resp.content}
    FOR    ${item}    IN    @{json}[data]
        IF    '${item}[name]' == '${TEST_PRODUCT_NAME}'
            DELETE API    /products/${item}[id]
            BREAK
        END
    END

*** Test Cases ***
TC_PROD_01_新增商品_成功
    ${body}=    Create Dictionary
    ...    name=${TEST_PRODUCT_NAME}
    ...    price=99.90
    ...    stock=50
    ...    description=自动化测试商品
    ${resp}=    POST API    /products    ${body}
    Should Be HTTP Status    ${resp}    201
    ${data}=    Get Response Data    ${resp}
    Set Suite Variable       ${PROD_ID}    ${data}[id]
    Should Be Equal As Numbers    ${data}[price]    99.9

TC_PROD_02_查询商品详情
    ${resp}=    GET API    /products/${PROD_ID}
    Should Be Code    ${resp}    200
    ${data}=    Get Response Data    ${resp}
    Should Be Equal    ${data}[name]    ${TEST_PRODUCT_NAME}

TC_PROD_03_编辑商品价格
    ${body}=    Create Dictionary    price=79.90    stock=30
    ${resp}=    PUT API    /products/${PROD_ID}    ${body}
    Should Be Code    ${resp}    200
    ${data}=    Get Response Data    ${resp}
    Should Be Equal As Numbers    ${data}[price]    79.9
    Should Be Equal As Integers   ${data}[stock]    30

TC_PROD_04_价格为负数_创建失败
    ${body}=    Create Dictionary    name=负价商品    price=-10    stock=1
    ${resp}=    POST API    /products    ${body}
    Should Be HTTP Status    ${resp}    400

TC_PROD_05_库存为负数_更新失败
    ${body}=    Create Dictionary    stock=-5
    ${resp}=    PUT API    /products/${PROD_ID}    ${body}
    Should Be HTTP Status    ${resp}    400

TC_PROD_06_缺少必填字段_name_创建失败
    ${body}=    Create Dictionary    price=10
    ${resp}=    POST API    /products    ${body}
    Should Be HTTP Status    ${resp}    400

TC_PROD_07_删除商品_成功
    ${resp}=    DELETE API    /products/${PROD_ID}
    Should Be Code    ${resp}    200
    ${resp2}=    GET API    /products/${PROD_ID}
    Should Be HTTP Status    ${resp2}    404