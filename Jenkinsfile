pipeline {
    agent any

    environment {
        PYTHON_ENV = "${WORKSPACE}/.venv"
        FLASK_APP = "app.py"
        BASE_URL = "http://localhost:8081"
    }

    triggers {
        // ✅ 实验六要求：定时执行（每天凌晨2点，可根据需要调整）
        cron('0 2 * * *')
    }

    stages {
        stage('环境准备') {
            steps {
                checkout scm
                bat """
                    python -m venv ${PYTHON_ENV}
                    ${PYTHON_ENV}\\Scripts\\activate.bat
                    pip install -r requirements.txt
                """
            }
        }

        stage('启动Flask服务') {
            steps {
                // 后台启动Flask，避免阻塞流水线
                bat """
                    ${PYTHON_ENV}\\Scripts\\activate.bat
                    start /B python ${FLASK_APP} > flask.log 2>&1
                    timeout /t 5 /nobreak > nul
                """
            }
        }

        stage('【实验三】Unittest接口测试') {
            steps {
                bat """
                    ${PYTHON_ENV}\\Scripts\\activate.bat
                    cd api_tests_unittest
                    python run.py
                """
            }
            post {
                always {
                    // ✅ 收集 Unittest XML 报告
                    junit 'api_tests_unittest/reports/result.xml'
                }
            }
        }

        stage('【实验四】Selenium UI测试') {
            steps {
                bat """
                    ${PYTHON_ENV}\\Scripts\\activate.bat
                    cd ui_tests
                    python run.py
                """
            }
            post {
                always {
                    junit 'ui_tests/reports/result.xml'
                }
            }
        }

        stage('【实验五】RobotFramework接口测试') {
            steps {
                bat """
                    ${PYTHON_ENV}\\Scripts\\activate.bat
                    robot --outputdir rf_api_tests/results ^
                          --variable BASE_URL:${BASE_URL} ^
                          rf_api_tests/tests/
                """
            }
            post {
                always {
                    // ✅ 收集 RF 专用报告
                    robot outputPath: 'rf_api_tests/results',
                          reportFileName: 'report.html',
                          logFileName: 'log.html',
                          outputFileName: 'output.xml',
                          passThreshold: 100,
                          unstableThreshold: 95
                }
            }
        }

        stage('停止Flask服务') {
            steps {
                bat 'taskkill /F /FI "WINDOWTITLE eq python*" /IM python.exe 2>nul || exit /b 0'
            }
        }
    }

    post {
        failure {
            echo '❌ 流水线执行失败，请检查各阶段报告'
        }
        success {
            echo '✅ 全部自动化测试通过'
        }
    }
}