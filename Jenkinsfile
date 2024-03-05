pipeline {
    agent none
    parameters {
        booleanParam(name: 'RUN_CHECKS', defaultValue: true, description: 'Run checks on code')
//        booleanParam(name: 'USE_SONARQUBE', defaultValue: true, description: 'Send data test data to SonarQube')
//        credentials(name: 'SONARCLOUD_TOKEN', credentialType: 'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl', defaultValue: 'sonarcloud_token', required: false)
//        booleanParam(name: 'TEST_RUN_TOX', defaultValue: false, description: 'Run Tox Tests')
//        booleanParam(name: 'BUILD_PACKAGES', defaultValue: false, description: 'Build Packages')
//        booleanParam(name: 'TEST_STANDALONE_PACKAGE_DEPLOYMENT', defaultValue: true, description: 'Test deploying any packages that are designed to be installed without using Python directly')
//        booleanParam(name: 'BUILD_CHOCOLATEY_PACKAGE', defaultValue: false, description: 'Build package for chocolatey package manager')
//        booleanParam(name: 'INCLUDE_LINUX_ARM', defaultValue: false, description: 'Include ARM architecture for Linux')
//        booleanParam(name: 'INCLUDE_LINUX_X86_64', defaultValue: true, description: 'Include x86_64 architecture for Linux')
//        booleanParam(name: 'INCLUDE_MACOS_ARM', defaultValue: false, description: 'Include ARM(m1) architecture for Mac')
//        booleanParam(name: 'INCLUDE_MACOS_X86_64', defaultValue: false, description: 'Include x86_64 architecture for Mac')
//        booleanParam(name: 'INCLUDE_WINDOWS_X86_64', defaultValue: true, description: 'Include x86_64 architecture for Windows')
//        booleanParam(name: 'TEST_PACKAGES', defaultValue: true, description: 'Test Python packages by installing them and running tests on the installed package')
//        booleanParam(name: 'PACKAGE_MAC_OS_STANDALONE_DMG', defaultValue: false, description: 'Create a Apple Application Bundle DMG')
//        booleanParam(name: 'PACKAGE_WINDOWS_STANDALONE_MSI', defaultValue: false, description: 'Create a standalone wix based .msi installer')
//        booleanParam(name: 'PACKAGE_WINDOWS_STANDALONE_NSIS', defaultValue: false, description: 'Create a standalone NULLSOFT NSIS based .exe installer')
//        booleanParam(name: 'PACKAGE_WINDOWS_STANDALONE_ZIP', defaultValue: false, description: 'Create a standalone portable package')
//        booleanParam(name: 'DEPLOY_DEVPI', defaultValue: false, description: "Deploy to DevPi on ${DEVPI_CONFIG.server}/DS_Jenkins/${env.BRANCH_NAME}")
//        booleanParam(name: 'DEPLOY_DEVPI_PRODUCTION', defaultValue: false, description: "Deploy to ${DEVPI_CONFIG.server}/production/release")
//        booleanParam(name: 'DEPLOY_PYPI', defaultValue: false, description: 'Deploy to pypi')
//        booleanParam(name: 'DEPLOY_CHOCOLATEY', defaultValue: false, description: 'Deploy to Chocolatey repository')
//        booleanParam(name: 'DEPLOY_STANDALONE_PACKAGERS', defaultValue: false, description: 'Deploy standalone packages')
//        booleanParam(name: 'DEPLOY_DOCS', defaultValue: false, description: 'Update online documentation')
    }
    stages {
//        stage('Build Sphinx Documentation'){
//            agent {
//                dockerfile {
//                    filename 'ci/docker/python/linux/jenkins/Dockerfile'
//                    label 'linux && docker && x86'
//                    additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
//                  }
//            }
//            options {
//                retry(conditions: [agent()], count: 2)
//            }
//            steps {
//                catchError(buildResult: 'UNSTABLE', message: 'Sphinx has warnings', stageResult: 'UNSTABLE') {
//                    buildSphinx()
//                }
//            }
//            post{
//                always{
//                    recordIssues(tools: [sphinxBuild(pattern: 'logs/build_sphinx_html.log')])
//                }
//                success{
//                    stash includes: 'dist/docs/*.pdf', name: 'SPEEDWAGON_DOC_PDF'
//                    zip archive: true, dir: 'build/docs/html', glob: '', zipFile: "dist/${props.name}-${props.version}.doc.zip"
//                    stash includes: 'dist/*.doc.zip,build/docs/html/**', name: 'DOCS_ARCHIVE'
//                    archiveArtifacts artifacts: 'dist/docs/*.pdf'
//                }
//                cleanup{
//                    cleanWs(
//                        notFailBuild: true,
//                        deleteDirs: true,
//                        patterns: [
//                            [pattern: 'dist/', type: 'INCLUDE'],
//                            [pattern: 'build/', type: 'INCLUDE'],
//                        ]
//                    )
//                }
//            }
//        }
        stage('Checks'){
            stages{
                stage('Code Quality'){
                    when{
                        equals expected: true, actual: params.RUN_CHECKS
                        beforeAgent true
                    }
                    agent any
//                    agent {
//                        dockerfile {
//                            filename 'ci/docker/python/linux/jenkins/Dockerfile'
//                            label 'linux && docker && x86'
//                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
//                            args '--mount source=sonar-cache-speedwagon,target=/opt/sonar/.sonar/cache'
//                          }
//                    }
                    options {
                        retry(conditions: [agent()], count: 2)
                    }
                    stages{
                        stage('Test') {
                            stages{
                                stage('Run Tests'){
                                    steps{
                                        echo "Running tests"
                                    }
//                                    parallel {
//                                        stage('Run PyTest Unit Tests'){
//                                            steps{
//                                                catchError(buildResult: 'UNSTABLE', message: 'Did not pass all pytest tests', stageResult: 'UNSTABLE') {
//                                                    sh(
//                                                        script: 'PYTHONFAULTHANDLER=1 coverage run --parallel-mode --source=speedwagon -m pytest --junitxml=./reports/tests/pytest/pytest-junit.xml --capture=no'
//                                                    )
//                                                }
//                                            }
//                                            post {
//                                                always {
//                                                    junit(allowEmptyResults: true, testResults: 'reports/tests/pytest/pytest-junit.xml')
//                                                    stash(allowEmpty: true, includes: 'reports/tests/pytest/*.xml', name: 'PYTEST_UNIT_TEST_RESULTS')
//                                                }
//                                            }
//                                        }
//                                        stage('Task Scanner'){
//                                            steps{
//                                                recordIssues(tools: [taskScanner(highTags: 'FIXME', includePattern: 'speedwagon/**/*.py', normalTags: 'TODO')])
//                                            }
//                                        }
//                                        stage('Audit Requirement Freeze File'){
//                                            steps{
//                                                catchError(buildResult: 'SUCCESS', message: 'pip-audit found issues', stageResult: 'UNSTABLE') {
//                                                    sh 'pip-audit -r requirements/requirements-gui-freeze.txt --cache-dir=/tmp/pip-audit-cache'
//                                                }
//                                            }
//                                        }
//                                        stage('Run Doctest Tests'){
//                                            steps {
//                                                sh(
//                                                    label: 'Running Doctest Tests',
//                                                    script: '''mkdir -p logs
//                                                               coverage run --parallel-mode --source=speedwagon -m sphinx -b doctest docs/source build/docs -d build/docs/doctrees --no-color -w logs/doctest.txt
//                                                               '''
//                                                    )
//                                            }
//                                            post{
//                                                always {
//                                                    recordIssues(tools: [sphinxBuild(id: 'doctest', name: 'Doctest', pattern: 'logs/doctest.txt')])
//                                                }
//                                            }
//                                        }
//                                        stage('Run MyPy Static Analysis') {
//                                            steps{
//                                                catchError(buildResult: 'SUCCESS', message: 'MyPy found issues', stageResult: 'UNSTABLE') {
//                                                    tee('logs/mypy.log'){
//                                                        sh(label: 'Running MyPy',
//                                                           script: 'mypy -p speedwagon --html-report reports/mypy/html'
//                                                        )
//                                                    }
//                                                }
//                                            }
//                                            post {
//                                                always {
//                                                    recordIssues(tools: [myPy(pattern: 'logs/mypy.log')])
//                                                    publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'reports/mypy/html/', reportFiles: 'index.html', reportName: 'MyPy HTML Report', reportTitles: ''])
//                                                }
//                                            }
//                                        }
//                                        stage('Run Pylint Static Analysis') {
//                                            steps{
//                                                run_pylint()
//                                            }
//                                            post{
//                                                always{
//                                                    stash includes: 'reports/pylint_issues.txt,reports/pylint.txt', name: 'PYLINT_REPORT'
//                                                    recordIssues(tools: [pyLint(pattern: 'reports/pylint_issues.txt')])
//                                                }
//                                            }
//                                        }
//                                        stage('Run Flake8 Static Analysis') {
//                                            steps{
//                                                catchError(buildResult: 'SUCCESS', message: 'Flake8 found issues', stageResult: 'UNSTABLE') {
//                                                    sh script: 'flake8 speedwagon -j 1 --tee --output-file=logs/flake8.log'
//                                                }
//                                            }
//                                            post {
//                                                always {
//                                                      stash includes: 'logs/flake8.log', name: 'FLAKE8_REPORT'
//                                                      recordIssues(tools: [flake8(pattern: 'logs/flake8.log')])
//                                                }
//                                            }
//                                        }
//                                        stage('pyDocStyle'){
//                                            steps{
//                                                catchError(buildResult: 'SUCCESS', message: 'Did not pass all pyDocStyle tests', stageResult: 'UNSTABLE') {
//                                                    sh(
//                                                        label: 'Run pydocstyle',
//                                                        script: '''mkdir -p reports
//                                                                   pydocstyle speedwagon > reports/pydocstyle-report.txt
//                                                                   '''
//                                                    )
//                                                }
//                                            }
//                                            post {
//                                                always{
//                                                    recordIssues(tools: [pyDocStyle(pattern: 'reports/pydocstyle-report.txt')])
//                                                }
//                                            }
//                                        }
//                                    }
//                                    post{
//                                        always{
//                                            sh 'coverage combine && coverage xml -o reports/coverage.xml && coverage html -d reports/coverage'
//                                            stash includes: 'reports/coverage.xml', name: 'COVERAGE_REPORT_DATA'
//                                            recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'reports/coverage.xml']])
//                                        }
//                                    }
                                }
                            }

                        }
//                        stage('Run Sonarqube Analysis'){
//                            options{
//                                lock('speedwagon-sonarscanner')
//                            }
//                            when{
//                                allOf{
//                                    equals expected: true, actual: params.USE_SONARQUBE
//                                    expression{
//                                        try{
//                                            withCredentials([string(credentialsId: params.SONARCLOUD_TOKEN, variable: 'dddd')]) {
//                                                echo 'Found credentials for sonarqube'
//                                            }
//                                        } catch(e){
//                                            return false
//                                        }
//                                        return true
//                                    }
//                                }
//                            }
//                            steps{
//                                script{
//                                    def sonarqube = load('ci/jenkins/scripts/sonarqube.groovy')
//                                    def sonarqubeConfig = [
//                                                installationName: 'sonarcloud',
//                                                credentialsId: params.SONARCLOUD_TOKEN,
//                                            ]
//                                    milestone label: 'sonarcloud'
//                                    if (env.CHANGE_ID){
//                                        sonarqube.submitToSonarcloud(
//                                            artifactStash: 'sonarqube artifacts',
//                                            sonarqube: sonarqubeConfig,
//                                            pullRequest: [
//                                                source: env.CHANGE_ID,
//                                                destination: env.BRANCH_NAME,
//                                            ],
//                                            package: [
//                                                version: props.version,
//                                                name: props.name
//                                            ],
//                                        )
//                                    } else {
//                                        sonarqube.submitToSonarcloud(
//                                            artifactStash: 'sonarqube artifacts',
//                                            sonarqube: sonarqubeConfig,
//                                            package: [
//                                                version: props.version,
//                                                name: props.name
//                                            ]
//                                        )
//                                    }
//                                }
//                            }
//                            post {
//                                always{
//                                    recordIssues(tools: [sonarQube(pattern: 'reports/sonar-report.json')])
//                                }
//                            }
//                        }
                    }
                    post{
                        cleanup{
                            cleanWs(patterns: [
                                    [pattern: 'logs/*', type: 'INCLUDE'],
                                    [pattern: 'reports/', type: 'INCLUDE'],
                                    [pattern: '.coverage', type: 'INCLUDE']
                                ])
                        }
//                        failure{
//                            sh 'pip list'
//                        }
                    }
                }
//                stage('Run Tox'){
//                    when{
//                        equals expected: true, actual: params.TEST_RUN_TOX
//                    }
//                    steps {
//                        runTox()
//                    }
//                }
            }
        }
    }
}