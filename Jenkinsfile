library identifier: 'JenkinsPythonHelperLibrary@2024.1.2', retriever: modernSCM(
  [$class: 'GitSCMSource',
   remote: 'https://github.com/UIUCLibrary/JenkinsPythonHelperLibrary.git',
   ])

BUNDLED_PYTHON_VERSION = '3.11.9'

SUPPORTED_MAC_VERSIONS = ['3.9', '3.10', '3.11']
SUPPORTED_LINUX_VERSIONS = ['3.8', '3.9', '3.10', '3.11']
SUPPORTED_WINDOWS_VERSIONS = ['3.8', '3.9', '3.10', '3.11']

def deployStandalone(glob, url) {
    script{
        findFiles(glob: glob).each{
            try{
                def encodedUrlFileName = new URI(null, null, it.name, null).toASCIIString()
                def putResponse = httpRequest authentication: NEXUS_CREDS, httpMode: 'PUT', uploadFile: it.path, url: "${url}/${encodedUrlFileName}", wrapAsMultipart: false
                echo "http request response: ${putResponse.content}"
                echo "Deployed ${it} -> SHA256: ${sha256(it.path)}"
            } catch(Exception e){
                echo "${e}"
                throw e;
            }
        }
    }
}

def getChocolateyServers() {
    retry(conditions: [agent()], count: 3) {
        node(){
            configFileProvider([configFile(fileId: 'deploymentStorageConfig', variable: 'CONFIG_FILE')]) {
                def config = readJSON( file: CONFIG_FILE)
                return config['chocolatey']['sources']
            }
        }
    }
}
def deploy_to_chocolatey(ChocolateyServer){
    script{
        def pkgs = []
        findFiles(glob: "packages/*.nupkg").each{
            pkgs << it.path
        }
        def deployment_options = input(
            message: 'Chocolatey server',
            parameters: [
                credentials(
                    credentialType: 'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl',
                    defaultValue: 'NEXUS_NUGET_API_KEY',
                    description: 'Nuget API key for Chocolatey',
                    name: 'CHOCO_REPO_KEY',
                    required: true
                ),
                choice(
                    choices: pkgs,
                    description: 'Package to use',
                    name: 'NUPKG'
                ),
            ]
        )
        withCredentials([string(credentialsId: deployment_options['CHOCO_REPO_KEY'], variable: 'KEY')]) {
            bat(
                label: "Deploying ${deployment_options['NUPKG']} to Chocolatey",
                script: "choco push ${deployment_options['NUPKG']} -s ${ChocolateyServer} -k %KEY%"
            )
        }
    }
}

def getDevpiConfig() {
    retry(conditions: [agent()], count: 3) {
        node(){
            configFileProvider([configFile(fileId: 'devpi_config', variable: 'CONFIG_FILE')]) {
                def configProperties = readProperties(file: CONFIG_FILE)
                configProperties.stagingIndex = {
                    if (env.TAG_NAME?.trim()){
                        return 'tag_staging'
                    } else{
                        return "${env.BRANCH_NAME}_staging"
                    }
                }()
                return configProperties
            }
        }
    }
}

def getStandAloneStorageServers(){
    retry(conditions: [agent()], count: 3) {
        node(){
            configFileProvider([configFile(fileId: 'deploymentStorageConfig', variable: 'CONFIG_FILE')]) {
                def config = readJSON( file: CONFIG_FILE)
                return config['publicReleases']['urls']
            }
        }
    }
}


def DEVPI_CONFIG = getDevpiConfig()

def getPypiConfig() {
    retry(conditions: [agent()], count: 3) {
        node(){
            configFileProvider([configFile(fileId: 'pypi_config', variable: 'CONFIG_FILE')]) {
                def config = readJSON( file: CONFIG_FILE)
                return config['deployment']['indexes']
            }
        }
    }
}


def testPythonPackages(){
    script{
        def windowsTests = [:]
        SUPPORTED_WINDOWS_VERSIONS.each{ pythonVersion ->
            if(params.INCLUDE_WINDOWS_X86_64 == true){
                windowsTests["Windows - Python ${pythonVersion}-x86: sdist"] = {
                    testPythonPkg(
                        agent: [
                            dockerfile: [
                                label: 'windows && docker && x86',
                                filename: 'ci/docker/windows/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE --build-arg chocolateyVersion --build-arg PIP_DOWNLOAD_CACHE=c:/users/containeradministrator/appdata/local/pip --build-arg UV_CACHE_DIR=c:/users/containeradministrator/appdata/local/uv'
                            ]
                        ],
                        retries: 3,
                        testSetup: {
                             checkout scm
                             unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                             findFiles(glob: 'dist/*.tar.gz,dist/*.zip').each{
                                powershell(label: 'Running Tox', script: "tox --installpkg ${it.path} --workdir \$env:TEMP\\tox  -e py${pythonVersion.replace('.', '')}-PySide6")
                             }

                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
                windowsTests["Windows - Python ${pythonVersion}-x86: wheel"] = {
                    testPythonPkg(
                        agent: [
                            dockerfile: [
                                label: 'windows && docker && x86',
                                filename: 'ci/docker/windows/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE --build-arg chocolateyVersion --build-arg PIP_DOWNLOAD_CACHE=c:/users/containeradministrator/appdata/local/pip --build-arg UV_CACHE_DIR=c:/users/containeradministrator/appdata/local/uv'
                            ]
                        ],
                        retries: 3,
                        testSetup: {
                             checkout scm
                             unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                             findFiles(glob: 'dist/*.whl').each{
                                 powershell(label: 'Running Tox', script: "tox --installpkg ${it.path} --workdir \$env:TEMP\\tox  -e py${pythonVersion.replace('.', '')}-PySide6")
                             }

                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
            }
        }
        def linuxTests = [:]
        SUPPORTED_LINUX_VERSIONS.each{ pythonVersion ->
            def architectures = []
            if(params.INCLUDE_LINUX_X86_64 == true){
                architectures.add('x86_64')
            }
            if(params.INCLUDE_LINUX_ARM == true){
                architectures.add('arm')
            }

            architectures.each{ processorArchitecture ->
                linuxTests["Linux-${processorArchitecture} - Python ${pythonVersion}: sdist"] = {
                    testPythonPkg(
                        agent: [
                            dockerfile: [
                                label: "linux && docker && ${processorArchitecture}",
                                filename: 'ci/docker/linux/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg PIP_DOWNLOAD_CACHE=/.cache/pip --build-arg UV_CACHE_DIR=/.cache/uv',
                                args: '-v pipcache_speedwagon_uiucprescon_workflows:/.cache/pip -v uvcache_speedwagon_uiucprescon_workflows:/.cache/uv'
                            ]
                        ],
                        retries: 3,
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                            findFiles(glob: 'dist/*.tar.gz').each{
                                sh(
                                    label: 'Running Tox',
                                    script: "tox --installpkg ${it.path} --workdir /tmp/tox -e py${pythonVersion}-PySide6"
                                    )
                            }
                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
                linuxTests["Linux-${processorArchitecture} - Python ${pythonVersion}: wheel"] = {
                    testPythonPkg(
                        agent: [
                            dockerfile: [
                                label: "linux && docker && ${processorArchitecture}",
                                filename: 'ci/docker/linux/tox/Dockerfile',
                                additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg PIP_DOWNLOAD_CACHE=/.cache/pip --build-arg UV_CACHE_DIR=/.cache/uv',
                                args: '-v pipcache_speedwagon_uiucprescon_workflows:/.cache/pip -v uvcache_speedwagon_uiucprescon_workflows:/.cache/uv'
                            ]
                        ],
                        retries: 3,
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                            findFiles(glob: 'dist/*.whl').each{
                                sh(
                                    label: 'Running Tox',
                                    script: "tox --installpkg ${it.path} --workdir /tmp/tox -e py${pythonVersion}-PySide6"
                                    )
                            }
                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
            }
        }
        def macTests = [:]

        SUPPORTED_MAC_VERSIONS.each{ pythonVersion ->
            def architectures = []
            if(params.INCLUDE_MACOS_X86_64 == true){
                architectures.add('x86_64')
            }
            if(params.INCLUDE_MACOS_ARM == true){
                architectures.add('m1')
            }
            architectures.each{ processorArchitecture ->
                macTests["Mac - ${processorArchitecture} - Python ${pythonVersion}: wheel"] = {
                    testPythonPkg(
                        agent: [
                            label: "mac && python${pythonVersion} && ${processorArchitecture}",
                        ],
                        retries: 3,
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                            findFiles(glob: 'dist/*.whl').each{
                                sh(label: 'Running Tox',
                                   script: """python${pythonVersion} -m venv venv
                                   ./venv/bin/python -m pip install --upgrade pip
                                   ./venv/bin/pip install -r requirements-dev.txt
                                   ./venv/bin/tox --installpkg ${it.path} -e py${pythonVersion.replace('.', '')}-PySide6"""
                                )
                            }

                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                            [pattern: '.tox/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
                macTests["Mac - ${processorArchitecture} - Python ${pythonVersion}: sdist"] = {
                    testPythonPkg(
                        agent: [
                            label: "mac && python${pythonVersion} && ${processorArchitecture}",
                        ],
                        retries: 3,
                        testSetup: {
                            checkout scm
                            unstash 'PYTHON_PACKAGES'
                        },
                        testCommand: {
                            findFiles(glob: 'dist/*.tar.gz').each{
                                sh(label: 'Running Tox',
                                   script: """python${pythonVersion} -m venv venv
                                   ./venv/bin/python -m pip install --upgrade pip
                                   ./venv/bin/pip install -r requirements-dev.txt
                                   ./venv/bin/tox --installpkg ${it.path} -e py${pythonVersion.replace('.', '')}-PySide6"""
                                )
                            }

                        },
                        post:[
                            cleanup: {
                                cleanWs(
                                    patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                            [pattern: '.tox/', type: 'INCLUDE'],
                                        ],
                                    notFailBuild: true,
                                    deleteDirs: true
                                )
                            },
                        ]
                    )
                }
            }
        }
        parallel(linuxTests + windowsTests + macTests)
    }
}

def get_packaging_scripts(){
    dir('speedwagon_scripts'){
        git branch: 'main', url: 'https://github.com/UIUCLibrary/speedwagon_scripts.git'
    }
}

def getMacDevpiTestStages(packageName, packageVersion, pythonVersions, devpiServer, devpiCredentialsId, devpiIndex) {
    node(){
        checkout scm
        devpi = load('ci/jenkins/scripts/devpi.groovy')
    }
    def macPackageStages = [:]
    pythonVersions.each{pythonVersion ->
        def macArchitectures = []
        if(params.INCLUDE_MACOS_X86_64 == true){
            macArchitectures.add('x86_64')
        }
        if(params.INCLUDE_MACOS_ARM == true){
            macArchitectures.add('m1')
        }
        macArchitectures.each{ processorArchitecture ->
            macPackageStages["Test Python ${pythonVersion}: wheel Mac ${processorArchitecture}"] = {
                withEnv([
                    'PATH+EXTRA=./venv/bin'
                    ]) {
                    devpi.testDevpiPackage(
                        agent: [
                            label: "mac && python${pythonVersion} && ${processorArchitecture} && devpi-access"
                        ],
                        devpi: [
                            index: devpiIndex,
                            server: devpiServer,
                            credentialsId: devpiCredentialsId,
                            devpiExec: 'venv/bin/devpi'
                        ],
                        package:[
                            name: packageName,
                            version: packageVersion,
                            selector: 'whl'
                        ],
                        test:[
                            setup: {
                                checkout scm
                                sh(
                                    label:'Installing Devpi client',
                                    script: '''python3 -m venv venv
                                                venv/bin/python -m pip install pip --upgrade
                                                venv/bin/python -m pip install 'devpi-client<7.0' -r requirements/requirements-dev.txt
                                                '''
                                )
                            },
                            toxEnv: "py${pythonVersion}".replace('.',''),
                            teardown: {
                                sh( label: 'Remove Devpi client', script: 'rm -r venv')
                            }
                        ],
                        retries: 3
                    )
                }
            }
            macPackageStages["Test Python ${pythonVersion}: sdist Mac ${processorArchitecture}"] = {
                withEnv([
                    'PATH+EXTRA=./venv/bin'
                    ]) {
                    devpi.testDevpiPackage(
                        agent: [
                            label: "mac && python${pythonVersion} && ${processorArchitecture} && devpi-access"
                        ],
                        devpi: [
                            index: devpiIndex,
                            server: devpiServer,
                            credentialsId: devpiCredentialsId,
                            devpiExec: 'venv/bin/devpi'
                        ],
                        package:[
                            name: packageName,
                            version: packageVersion,
                            selector: 'whl'
                        ],
                        test:[
                            setup: {
                                checkout scm
                                sh(
                                    label:'Installing Devpi client',
                                    script: '''python3 -m venv venv
                                                venv/bin/python -m pip install pip --upgrade
                                                venv/bin/python -m pip install 'devpi-client<7.0' -r requirements/requirements-dev.txt
                                                '''
                                )
                            },
                            toxEnv: "py${pythonVersion}".replace('.',''),
                            teardown: {
                                sh( label: 'Remove Devpi client', script: 'rm -r venv')
                            }
                        ],
                        retries: 3
                    )
                }
            }
        }
    }
    return macPackageStages;
}



def get_props(){
    stage('Reading Package Metadata'){
        node('docker && linux') {
            checkout scm
            docker.image('python').inside {
                def packageMetadata = readJSON text: sh(returnStdout: true, script: 'python -c \'import tomllib;print(tomllib.load(open("pyproject.toml", "rb"))["project"])\'').trim()
                echo """Metadata:

    Name      ${packageMetadata.name}
    Version   ${packageMetadata.version}
    """
                return packageMetadata
            }
        }
    }
}

def buildSphinx(){
    def sphinx  = load('ci/jenkins/scripts/sphinx.groovy')
    sh(script: '''mkdir -p logs
                  '''
      )

    sphinx.buildSphinxDocumentation(
        sourceDir: 'docs',
        outputDir: 'build/docs/html',
        doctreeDir: 'build/docs/.doctrees',
        builder: 'html',
        writeWarningsToFile: 'logs/build_sphinx_html.log'
        )
    sphinx.buildSphinxDocumentation(
        sourceDir: 'docs',
        outputDir: 'build/docs/latex',
        doctreeDir: 'build/docs/.doctrees',
        builder: 'latex'
        )

    sh(label: 'Building PDF docs',
       script: '''make -C build/docs/latex
                  mkdir -p dist/docs
                  mv build/docs/latex/*.pdf dist/docs/
                  '''
    )
}

props = get_props()

pipeline {
    agent none
    parameters {
        booleanParam(name: 'RUN_CHECKS', defaultValue: true, description: 'Run checks on code')
        booleanParam(name: 'USE_SONARQUBE', defaultValue: true, description: 'Send data test data to SonarQube')
        credentials(name: 'SONARCLOUD_TOKEN', credentialType: 'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl', defaultValue: 'sonarcloud_token', required: false)
        booleanParam(name: 'TEST_RUN_TOX', defaultValue: false, description: 'Run Tox Tests')
        booleanParam(name: 'BUILD_PACKAGES', defaultValue: false, description: 'Build Packages')
        booleanParam(name: 'INCLUDE_LINUX_ARM', defaultValue: false, description: 'Include ARM architecture for Linux')
        booleanParam(name: 'INCLUDE_LINUX_X86_64', defaultValue: true, description: 'Include x86_64 architecture for Linux')
        booleanParam(name: 'INCLUDE_MACOS_ARM', defaultValue: false, description: 'Include ARM(m1) architecture for Mac')
        booleanParam(name: 'INCLUDE_MACOS_X86_64', defaultValue: false, description: 'Include x86_64 architecture for Mac')
        booleanParam(name: 'INCLUDE_WINDOWS_X86_64', defaultValue: true, description: 'Include x86_64 architecture for Windows')
        booleanParam(name: 'TEST_PACKAGES', defaultValue: true, description: 'Test Python packages by installing them and running tests on the installed package')
        booleanParam(name: 'PACKAGE_MAC_OS_STANDALONE_DMG', defaultValue: false, description: 'Create a Apple Application Bundle DMG')
        booleanParam(name: 'PACKAGE_STANDALONE_WINDOWS_INSTALLER', defaultValue: false, description: 'Create a standalone wix based .msi installer')
        booleanParam(name: 'DEPLOY_DEVPI', defaultValue: false, description: "Deploy to DevPi on ${DEVPI_CONFIG.server}/DS_Jenkins/${env.BRANCH_NAME}")
        booleanParam(name: 'DEPLOY_DEVPI_PRODUCTION', defaultValue: false, description: "Deploy to ${DEVPI_CONFIG.server}/production/release")
        booleanParam(name: 'DEPLOY_PYPI', defaultValue: false, description: 'Deploy to pypi')
        booleanParam(name: 'DEPLOY_STANDALONE_PACKAGERS', defaultValue: false, description: 'Deploy standalone packages')
        booleanParam(name: 'DEPLOY_DOCS', defaultValue: false, description: 'Update online documentation')
    }
    stages {
        stage('Build Sphinx Documentation'){
            agent {
                dockerfile {
                    filename 'ci/docker/linux/jenkins/Dockerfile'
                    label 'linux && docker && x86'
                    additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                    args '--mount source=sonar-cache-uiucprescon_workflows,target=/opt/sonar/.sonar/cache'
                  }
            }
            options {
                retry(conditions: [agent()], count: 2)
            }
            steps {
                catchError(buildResult: 'UNSTABLE', message: 'Sphinx has warnings', stageResult: 'UNSTABLE') {
                    buildSphinx()
                }
            }
            post{
                always{
                    recordIssues(tools: [sphinxBuild(pattern: 'logs/build_sphinx_html.log')])
                }
                success{
                    stash includes: 'dist/docs/*.pdf', name: 'SPEEDWAGON_DOC_PDF'
                    zip archive: true, dir: 'build/docs/html', glob: '', zipFile: "dist/${props.name}-${props.version}.doc.zip"
                    stash includes: 'dist/*.doc.zip,build/docs/html/**', name: 'DOCS_ARCHIVE'
                    archiveArtifacts artifacts: 'dist/docs/*.pdf'
                }
                cleanup{
                    cleanWs(
                        notFailBuild: true,
                        deleteDirs: true,
                        patterns: [
                            [pattern: 'dist/', type: 'INCLUDE'],
                            [pattern: 'build/', type: 'INCLUDE'],
                        ]
                    )
                }
            }
        }
        stage('Checks'){
            stages{
                stage('Code Quality'){
                    when{
                        equals expected: true, actual: params.RUN_CHECKS
                        beforeAgent true
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/linux/jenkins/Dockerfile'
                            label 'linux && docker && x86'
                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                            args '--mount source=sonar-cache-uiucprescon_workflows,target=/opt/sonar/.sonar/cache'
                          }
                    }
                    options {
                        retry(conditions: [agent()], count: 2)
                    }
                    stages{
                        stage('Test') {
                            stages{
                                stage('Setup Tests'){
                                    steps{
                                        sh 'mkdir -p reports'
                                    }
                                }
                                stage('Run Tests'){
                                    parallel {
                                        stage('Run PyTest Unit Tests'){
                                            steps{
                                                catchError(buildResult: 'UNSTABLE', message: 'Did not pass all pytest tests', stageResult: 'UNSTABLE') {
                                                    sh(
                                                        script: 'PYTHONFAULTHANDLER=1 coverage run --parallel-mode --source=speedwagon_uiucprescon -m pytest --junitxml=./reports/tests/pytest/pytest-junit.xml --capture=no'
                                                    )
                                                }
                                            }
                                            post {
                                                always {
                                                    junit(allowEmptyResults: true, testResults: 'reports/tests/pytest/pytest-junit.xml')
                                                    stash(allowEmpty: true, includes: 'reports/tests/pytest/*.xml', name: 'PYTEST_UNIT_TEST_RESULTS')
                                                }
                                            }
                                        }
                                        stage('Task Scanner'){
                                            steps{
                                                recordIssues(tools: [taskScanner(highTags: 'FIXME', includePattern: 'speedwagon_uiucprescon/**/*.py', normalTags: 'TODO')])
                                            }
                                        }
                                        stage('Audit Requirement Freeze File'){
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'pip-audit found issues', stageResult: 'UNSTABLE') {
                                                    sh 'pip-audit -r requirements/requirements-vendor.txt --cache-dir=/tmp/pip-audit-cache'
                                                }
                                            }
                                        }
                                        stage('Run Doctest Tests'){
                                            steps {
                                                sh(
                                                    label: 'Running Doctest Tests',
                                                    script: '''mkdir -p logs
                                                               coverage run --parallel-mode --source=speedwagon_uiucprescon -m sphinx -b doctest docs build/docs -d build/docs/doctrees --no-color -w logs/doctest.txt
                                                               '''
                                                    )
                                            }
                                            post{
                                                always {
                                                    recordIssues(tools: [sphinxBuild(id: 'doctest', name: 'Doctest', pattern: 'logs/doctest.txt')])
                                                }
                                            }
                                        }
                                        stage('Run MyPy Static Analysis') {
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'MyPy found issues', stageResult: 'UNSTABLE') {
                                                    tee('logs/mypy.log'){
                                                        sh(label: 'Running MyPy',
                                                           script: 'mypy -p speedwagon_uiucprescon --html-report reports/mypy/html'
                                                        )
                                                    }
                                                }
                                            }
                                            post {
                                                always {
                                                    recordIssues(tools: [myPy(pattern: 'logs/mypy.log')])
                                                    publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: false, reportDir: 'reports/mypy/html/', reportFiles: 'index.html', reportName: 'MyPy HTML Report', reportTitles: ''])
                                                }
                                            }
                                        }
                                        stage('Run Pylint Static Analysis') {
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'Pylint found issues', stageResult: 'UNSTABLE') {
                                                    sh(label: 'Running pylint',
                                                        script: 'pylint speedwagon_uiucprescon -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > reports/pylint.txt'
                                                    )
                                                }
                                                sh(
                                                    script: 'pylint speedwagon_uiucprescon -r n --msg-template="{path}:{module}:{line}: [{msg_id}({symbol}), {obj}] {msg}" | tee reports/pylint_issues.txt',
                                                    label: 'Running pylint for sonarqube',
                                                    returnStatus: true
                                                )
                                            }
                                            post{
                                                always{
                                                    recordIssues(tools: [pyLint(pattern: 'reports/pylint.txt')])
                                                    stash includes: 'reports/pylint_issues.txt,reports/pylint.txt', name: 'PYLINT_REPORT'
                                                }
                                            }
                                        }
                                        stage('Run Flake8 Static Analysis') {
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'Flake8 found issues', stageResult: 'UNSTABLE') {
                                                    sh script: 'flake8 speedwagon_uiucprescon -j 1 --tee --output-file=logs/flake8.log'
                                                }
                                            }
                                            post {
                                                always {
                                                      stash includes: 'logs/flake8.log', name: 'FLAKE8_REPORT'
                                                      recordIssues(tools: [flake8(pattern: 'logs/flake8.log')])
                                                }
                                            }
                                        }
                                        stage('pyDocStyle'){
                                            steps{
                                                catchError(buildResult: 'SUCCESS', message: 'Did not pass all pyDocStyle tests', stageResult: 'UNSTABLE') {
                                                    sh(
                                                        label: 'Run pydocstyle',
                                                        script: '''mkdir -p reports
                                                                   pydocstyle speedwagon_uiucprescon > reports/pydocstyle-report.txt
                                                                   '''
                                                    )
                                                }
                                            }
                                            post {
                                                always{
                                                    recordIssues(tools: [pyDocStyle(pattern: 'reports/pydocstyle-report.txt')])
                                                }
                                            }
                                        }
                                    }
                                    post{
                                        always{
                                            sh 'coverage combine && coverage xml -o reports/coverage.xml && coverage html -d reports/coverage'
                                            stash includes: 'reports/coverage.xml', name: 'COVERAGE_REPORT_DATA'
                                            recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'reports/coverage.xml']])
                                        }
                                    }
                                }
                            }

                        }
                        stage('Run Sonarqube Analysis'){
                            options{
                                lock('uiucpreson_workflows-sonarscanner')
                            }
                            when{
                                allOf{
                                    equals expected: true, actual: params.USE_SONARQUBE
                                    expression{
                                        try{
                                            withCredentials([string(credentialsId: params.SONARCLOUD_TOKEN, variable: 'dddd')]) {
                                                echo 'Found credentials for sonarqube'
                                            }
                                        } catch(e){
                                            return false
                                        }
                                        return true
                                    }
                                }
                            }
                            steps{
                                script{
                                    def sonarqube = load('ci/jenkins/scripts/sonarqube.groovy')
                                    def sonarqubeConfig = [
                                        installationName: 'sonarcloud',
                                        credentialsId: params.SONARCLOUD_TOKEN,
                                    ]
                                    milestone label: 'sonarcloud'
                                    if (env.CHANGE_ID){
                                        sonarqube.submitToSonarcloud(
                                            artifactStash: 'sonarqube artifacts',
                                            sonarqube: sonarqubeConfig,
                                            pullRequest: [
                                                source: env.CHANGE_ID,
                                                destination: env.BRANCH_NAME,
                                            ],
                                            package: [
                                                version: props.version,
                                                name: props.name
                                            ],
                                        )
                                    } else {
                                        sonarqube.submitToSonarcloud(
                                            artifactStash: 'sonarqube artifacts',
                                            sonarqube: sonarqubeConfig,
                                            package: [
                                                version: props.version,
                                                name: props.name
                                            ]
                                        )
                                    }
                                }
                            }
                            post {
                                always{
                                    recordIssues(tools: [sonarQube(pattern: 'reports/sonar-report.json')])
                                }
                            }
                        }
                    }
                    post{
                        cleanup{
                            cleanWs(patterns: [
                                    [pattern: 'logs/*', type: 'INCLUDE'],
                                    [pattern: 'reports/', type: 'INCLUDE'],
                                    [pattern: '.coverage', type: 'INCLUDE']
                                ])
                        }
                        failure{
                            sh 'pip list'
                        }
                    }
                }
                stage('Tox'){
                    when{
                        equals expected: true, actual: params.TEST_RUN_TOX
                    }
                    options {
                        lock(env.JOB_URL)
                    }
                    steps {
                        script{
                            def windowsJobs
                            def linuxJobs
                            stage('Scanning Tox Environments'){
                                parallel(
                                    'Linux':{
                                        linuxJobs = getToxTestsParallel(
                                                envNamePrefix: 'Tox Linux',
                                                label: 'linux && docker',
                                                dockerfile: 'ci/docker/linux/tox/Dockerfile',
                                                dockerArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg PIP_DOWNLOAD_CACHE=/.cache/pip --build-arg UV_CACHE_DIR=/.cache/uv',
                                                dockerRunArgs: '-v pipcache_speedwagon_uiucprescon_workflows:/.cache/pip -v uvcache_speedwagon_uiucprescon_workflows:/.cache/uv',
                                                retry: 2
                                            )
                                    },
                                    'Windows':{
                                        windowsJobs = getToxTestsParallel(
                                                envNamePrefix: 'Tox Windows',
                                                label: 'windows && docker',
                                                dockerfile: 'ci/docker/windows/tox/Dockerfile',
                                                dockerArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE --build-arg chocolateyVersion --build-arg PIP_DOWNLOAD_CACHE=c:/users/containeradministrator/appdata/local/pip --build-arg UV_CACHE_DIR=c:/users/containeradministrator/appdata/local/uv',
                                                dockerRunArgs: '-v pipcache_speedwagon_uiucprescon_workflows:c:/users/containeradministrator/appdata/local/pip -v uvcache_speedwagon_uiucprescon_workflows:c:/users/containeradministrator/appdata/local/uv',
                                                retry: 2

                                            )
                                    },
                                    failFast: true
                                )
                            }
                            stage('Run Tox'){
                                parallel(windowsJobs + linuxJobs)
                            }
                        }
                    }
                }
            }
        }
        stage('Packaging'){
            when{
                anyOf{
                    equals expected: true, actual: params.BUILD_PACKAGES
                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                    equals expected: true, actual: params.PACKAGE_STANDALONE_WINDOWS_INSTALLER
                    equals expected: true, actual: params.DEPLOY_DEVPI
                    equals expected: true, actual: params.DEPLOY_DEVPI_PRODUCTION
                }
                beforeAgent true
            }
            stages{
                stage('Python Packages'){
                    stages{
                        stage('Packaging sdist and wheel'){
                            agent {
                                docker{
                                    image 'python'
                                    label 'linux && docker'
                                }
                            }
                            options {
                                timeout(5)
                            }
                            steps{
                                withEnv(['PIP_NO_CACHE_DIR=off']) {
                                    sh(label: 'Building Python Package',
                                       script: '''python -m venv venv --upgrade-deps
                                                  venv/bin/pip install build
                                                  venv/bin/python -m build .
                                                  '''
                                       )
                               }
                            }
                            post{
                                always{
                                    stash includes: 'dist/*.whl,dist/*.tar.gz,dist/*.zip', name: 'PYTHON_PACKAGES'
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                            [pattern: 'dist/', type: 'INCLUDE']
                                            ]
                                        )
                                }
                            }
                        }
                        stage('Testing Python Package'){
                            when{
                                equals expected: true, actual: params.TEST_PACKAGES
                            }
                            steps{
                                testPythonPackages()
                            }
                        }
                    }
                }
                stage('End-user packages'){
                    parallel{
                        stage('Mac Application Bundle x86_64'){
                            agent{
                                label 'mac && python3.11 && x86_64'
                            }
                            when{
                                allOf{
                                    equals expected: true, actual: params.INCLUDE_MACOS_X86_64
                                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                    expression {return nodesByLabel('mac && python3.11 && x86_64').size() > 0}
                                }
                                beforeInput true
                            }
                            steps{
                                get_packaging_scripts()
                                unstash 'PYTHON_PACKAGES'
                                script{
                                    findFiles(glob: 'dist/*.whl').each{ wheel ->
                                        sh "./contrib/make_standalone.sh --base-python-path python3.11 --venv-path ./venv ${wheel} -r requirements.txt"
                                    }
                                }
                            }
                            post{
                                success{
                                    archiveArtifacts artifacts: 'dist/*.dmg', fingerprint: true
                                    stash includes: 'dist/*.dmg', name: 'APPLE_APPLICATION_BUNDLE_X86_64'
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: 'build/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                        ]
                                    )
                                }
                            }
                        }
                        stage('Mac Application Bundle M1'){
                            agent{
                                label 'mac && python3.11 && arm64'
                            }
                            when{
                                allOf{
                                    equals expected: true, actual: params.INCLUDE_MACOS_ARM
                                    equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                    expression {return nodesByLabel('mac && python3.11 && arm64').size() > 0}
                                }
                                beforeInput true
                            }
                            steps{
                                script{
                                    get_packaging_scripts()
                                    unstash 'PYTHON_PACKAGES'
                                    findFiles(glob: 'dist/*.whl').each{ wheel ->
                                        sh "./speedwagon_scripts/make_standalone.sh --base-python-path python3.11 --venv-path ./venv ${wheel} -r requirements.txt"
                                    }
                                }
                            }
                            post{
                                success{
                                    archiveArtifacts artifacts: 'dist/*.dmg', fingerprint: true
                                    stash includes: 'dist/*.dmg', name: 'APPLE_APPLICATION_BUNDLE_M1'
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: 'build/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                        ]
                                    )
                                }
                            }
                        }
                        stage('Windows Installer for x86_64'){
                            agent {
                                dockerfile {
                                    filename 'ci/docker/windows/tox/Dockerfile'
                                    label 'windows && docker && x86'
                                    additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE --build-arg chocolateyVersion --build-arg PIP_DOWNLOAD_CACHE=c:/users/containeradministrator/appdata/local/pip --build-arg UV_CACHE_DIR=c:/users/containeradministrator/appdata/local/uv'
                                    args '-v pipcache_speedwagon_uiucprescon_workflows:c:/users/containeradministrator/appdata/local/pip -v uvcache_speedwagon_uiucprescon_workflows:c:/users/containeradministrator/appdata/local/uv'
                                  }
                            }
                            when{
                                equals expected: true, actual: params.PACKAGE_STANDALONE_WINDOWS_INSTALLER
                            }
                            steps{
                                unstash 'PYTHON_PACKAGES'
                                script{
                                    get_packaging_scripts()
                                    findFiles(glob: 'dist/*.whl').each{
                                        bat(
                                            label: 'Create standalone windows version',
                                            script: "speedwagon_scripts/make_standalone.bat --base-python-path \"py -3.11\" --venv-path .\\venv ${it} -r requirements.txt"
                                        )
                                    }
                                }
                            }
                            post{
                                success{
                                    archiveArtifacts artifacts: 'dist/*.msi', fingerprint: true
                                    stash includes: 'dist/*.msi', name: 'STANDALONE_WINDOWS_INSTALLER'
                                }
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'build/', type: 'INCLUDE'],
                                            [pattern: 'dist/', type: 'INCLUDE'],
                                            [pattern: 'venv/', type: 'INCLUDE'],
                                        ]
                                    )
                                }
                            }
                        }
                    }
                }
                stage('Deploy to Devpi'){
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_DEVPI
                            anyOf {
                                equals expected: 'master', actual: env.BRANCH_NAME
                                equals expected: 'dev', actual: env.BRANCH_NAME
                                tag '*'
                            }
                        }
                        beforeAgent true
                        beforeOptions true
                    }
                    agent none
                    options{
                        lock(env.JOB_URL)
                    }
                    stages{
                        stage('Deploy to Devpi Staging') {
                            agent {
                                dockerfile {
                                    filename 'ci/docker/linux/jenkins/Dockerfile'
                                    label 'linux && docker && devpi-access'
                                    additionalBuildArgs ' --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                                  }
                            }
                            steps {
                                // milestone label: 'devpi_deploy'
                                unstash 'DOCS_ARCHIVE'
                                unstash 'PYTHON_PACKAGES'
                                script{
                                    load('ci/jenkins/scripts/devpi.groovy').upload(
                                            server: DEVPI_CONFIG.server,
                                            credentialsId: DEVPI_CONFIG.credentialsId,
                                            index: DEVPI_CONFIG.stagingIndex,
                                            clientDir: './devpi'
                                        )
                                }
                            }
                        }
                        stage('Test DevPi packages') {
                            steps{
                                script{
                                    def devpi
                                    node(){
                                        checkout scm
                                        devpi = load('ci/jenkins/scripts/devpi.groovy')
                                    }
                                    def macPackages = getMacDevpiTestStages(props.name, props.version, SUPPORTED_MAC_VERSIONS, DEVPI_CONFIG.server, DEVPI_CONFIG.credentialsId, DEVPI_CONFIG.stagingIndex)
                                    windowsPackages = [:]
                                    SUPPORTED_WINDOWS_VERSIONS.each{pythonVersion ->
                                        if(params.INCLUDE_WINDOWS_X86_64 == true){
                                            windowsPackages["Test Python ${pythonVersion}: sdist Windows"] = {
                                                devpi.testDevpiPackage(
                                                    agent: [
                                                        dockerfile: [
                                                            filename: 'ci/docker/windows/tox/Dockerfile',
                                                            additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE --build-arg chocolateyVersion --build-arg PIP_DOWNLOAD_CACHE=c:/users/containeradministrator/appdata/local/pip --build-arg UV_CACHE_DIR=c:/users/containeradministrator/appdata/local/uv',
                                                            label: 'windows && docker && x86 && devpi-access'
                                                        ]
                                                    ],
                                                    devpi: [
                                                        index: DEVPI_CONFIG.stagingIndex,
                                                        server: DEVPI_CONFIG.server,
                                                        credentialsId: DEVPI_CONFIG.credentialsId,
                                                    ],
                                                    package:[
                                                        name: props.name,
                                                        version: props.version,
                                                        selector: 'tar.gz'
                                                    ],
                                                    test:[
                                                        toxEnv: "py${pythonVersion}".replace('.',''),
                                                    ],
                                                    retries: 3
                                                )
                                            }
                                            windowsPackages["Test Python ${pythonVersion}: wheel Windows"] = {
                                                devpi.testDevpiPackage(
                                                    agent: [
                                                        dockerfile: [
                                                            filename: 'ci/docker/windows/tox/Dockerfile',
                                                            additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg CHOCOLATEY_SOURCE --build-arg chocolateyVersion --build-arg PIP_DOWNLOAD_CACHE=c:/users/containeradministrator/appdata/local/pip --build-arg UV_CACHE_DIR=c:/users/containeradministrator/appdata/local/uv',
                                                            label: 'windows && docker && x86 && devpi-access'
                                                        ]
                                                    ],
                                                    devpi: [
                                                        index: DEVPI_CONFIG.stagingIndex,
                                                        server: DEVPI_CONFIG.server,
                                                        credentialsId: DEVPI_CONFIG.credentialsId,
                                                    ],
                                                    package:[
                                                        name: props.name,
                                                        version: props.version,
                                                        selector: 'whl'
                                                    ],
                                                    test:[
                                                        toxEnv: "py${pythonVersion}".replace('.',''),
                                                    ],
                                                    retries: 3
                                                )
                                            }
                                        }
                                    }
                                    def linuxPackages = [:]
                                    SUPPORTED_LINUX_VERSIONS.each{pythonVersion ->
                                        if(params.INCLUDE_LINUX_X86_64 == true){
                                            linuxPackages["Test Python ${pythonVersion}: sdist Linux"] = {
                                                devpi.testDevpiPackage(
                                                    agent: [
                                                        dockerfile: [
                                                            filename: 'ci/docker/linux/tox/Dockerfile',
                                                            additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg PIP_DOWNLOAD_CACHE=/.cache/pip --build-arg UV_CACHE_DIR=/.cache/uv',
                                                            label: 'linux && docker && x86 && devpi-access',
                                                            args: '-v pipcache_speedwagon_uiucprescon_workflows:/.cache/pip -v uvcache_speedwagon_uiucprescon_workflows:/.cache/uv'
                                                        ]
                                                    ],
                                                    devpi: [
                                                        index: DEVPI_CONFIG.stagingIndex,
                                                        server: DEVPI_CONFIG.server,
                                                        credentialsId: DEVPI_CONFIG.credentialsId,
                                                    ],
                                                    package:[
                                                        name: props.name,
                                                        version: props.version,
                                                        selector: 'tar.gz'
                                                    ],
                                                    test:[
                                                        toxEnv: "py${pythonVersion}".replace('.',''),
                                                    ],
                                                    retries: 3
                                                )
                                            }
                                            linuxPackages["Test Python ${pythonVersion}: wheel Linux"] = {
                                                devpi.testDevpiPackage(
                                                    agent: [
                                                        dockerfile: [
                                                            filename: 'ci/docker/linux/tox/Dockerfile',
                                                            additionalBuildArgs: '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL --build-arg PIP_DOWNLOAD_CACHE=/.cache/pip --build-arg UV_CACHE_DIR=/.cache/uv',
                                                            label: 'linux && docker && x86 && devpi-access',
                                                            args: '-v pipcache_speedwagon_uiucprescon_workflows:/.cache/pip -v uvcache_speedwagon_uiucprescon_workflows:/.cache/uv'
                                                        ]
                                                    ],
                                                    devpi: [
                                                        index: DEVPI_CONFIG.stagingIndex,
                                                        server: DEVPI_CONFIG.server,
                                                        credentialsId: DEVPI_CONFIG.credentialsId,
                                                    ],
                                                    package:[
                                                        name: props.name,
                                                        version: props.version,
                                                        selector: 'whl'
                                                    ],
                                                    test:[
                                                        toxEnv: "py${pythonVersion}".replace('.',''),
                                                    ],
                                                    retries: 3
                                                )
                                            }
                                        }
                                    }
                                    parallel(linuxPackages + windowsPackages + macPackages)
                                }
                            }
                        }
                        stage('Deploy to DevPi Production') {
                            when {
                                allOf{
                                    equals expected: true, actual: params.DEPLOY_DEVPI_PRODUCTION

                                    anyOf {
                                        equals expected: 'master', actual: env.BRANCH_NAME
                                        tag '*'
                                    }
                                }
                                beforeAgent true
                                beforeInput true
                            }
                            agent {
                                dockerfile {
                                    filename 'ci/docker/linux/jenkins/Dockerfile'
                                    label 'linux && docker && devpi-access'
                                    additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                                  }
                            }
                            input {
                                message 'Release to DevPi Production?'
                            }
                            steps {
                                script{
                                    load('ci/jenkins/scripts/devpi.groovy').pushPackageToIndex(
                                        pkgName: props.name,
                                        pkgVersion: props.version,
                                        server: DEVPI_CONFIG.server,
                                        indexSource: DEVPI_CONFIG.stagingIndex,
                                        indexDestination: 'production/release',
                                        credentialsId: DEVPI_CONFIG.credentialsId
                                    )
                                }
                            }
                        }
                    }
                    post{
                        success{
                            node('linux && docker && devpi-access') {
                               script{
                                    if (!env.TAG_NAME?.trim()){
                                        checkout scm
                                        def dockerImage = docker.build('speedwagon:devpi','-f ./ci/docker/linux/jenkins/Dockerfile --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL .')
                                        dockerImage.inside{
                                            load('ci/jenkins/scripts/devpi.groovy').pushPackageToIndex(
                                                pkgName: props.name,
                                                pkgVersion: props.version,
                                                server: DEVPI_CONFIG.server,
                                                indexSource: DEVPI_CONFIG.stagingIndex,
                                                indexDestination: "DS_Jenkins/${env.BRANCH_NAME}",
                                                credentialsId: DEVPI_CONFIG.credentialsId,
                                            )
                                        }
                                        sh script: "docker image rm --no-prune ${dockerImage.imageName()}"
                                   }
                               }
                            }
                        }
                        cleanup{
                            node('linux && docker && x86 && devpi-access') {
                               script{
                                    checkout scm
                                    def dockerImage = docker.build('speedwagon:devpi','-f ./ci/docker/linux/jenkins/Dockerfile --build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL .')
                                    dockerImage.inside{
                                        load('ci/jenkins/scripts/devpi.groovy').removePackage(
                                            pkgName: props.name,
                                            pkgVersion: props.version,
                                            index: DEVPI_CONFIG.stagingIndex,
                                            server: DEVPI_CONFIG.server,
                                            credentialsId: DEVPI_CONFIG.credentialsId,

                                        )
                                    }
                                    sh script: "docker image rm --no-prune ${dockerImage.imageName()}"
                               }
                            }
                        }
                    }
                }
            }
        }
        stage('Deploy'){
            when{
                anyOf {
                    equals expected: true, actual:  params.DEPLOY_PYPI
                    equals expected: true, actual:  params.DEPLOY_STANDALONE_PACKAGERS
                    equals expected: true, actual:  params.DEPLOY_DOCS
                }
                beforeOptions true
            }
            options{
                lock('uiucpreson_workflows-deploy')
            }
            parallel {
                stage('Deploy to pypi') {
                    agent {
                        dockerfile {
                            filename 'ci/docker/linux/jenkins/Dockerfile'
                            label 'linux && docker'
                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                        }
                    }
                    when{
                        allOf{
                            equals expected: true, actual: params.DEPLOY_PYPI
                            equals expected: true, actual: params.BUILD_PACKAGES
                        }
                        beforeAgent true
                        beforeInput true
                    }
                    options{
                        retry(3)
                    }
                    input {
                        message 'Upload to pypi server?'
                        parameters {
                            choice(
                                choices: getPypiConfig(),
                                description: 'Url to the pypi index to upload python packages.',
                                name: 'SERVER_URL'
                            )
                        }
                    }
                    steps{
                        unstash 'PYTHON_PACKAGES'
                        pypiUpload(
                            credentialsId: 'jenkins-nexus',
                            repositoryUrl: SERVER_URL,
                            glob: 'dist/*'
                        )
                    }
                    post{
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                        [pattern: 'dist/', type: 'INCLUDE']
                                    ]
                            )
                        }
                    }
                }
                stage('Deploy Online Documentation') {
                    when{
                        equals expected: true, actual: params.DEPLOY_DOCS
                        beforeAgent true
                        beforeInput true
                    }
                    agent {
                        dockerfile {
                            filename 'ci/docker/linux/jenkins/Dockerfile'
                            label 'linux && docker'
                            additionalBuildArgs '--build-arg PIP_EXTRA_INDEX_URL --build-arg PIP_INDEX_URL'
                          }
                    }
                    options{
                        timeout(time: 1, unit: 'DAYS')
                    }
                    input {
                        message 'Update project documentation?'
                    }
                    steps{
                        unstash 'DOCS_ARCHIVE'
                        withCredentials([usernamePassword(credentialsId: 'dccdocs-server', passwordVariable: 'docsPassword', usernameVariable: 'docsUsername')]) {
                            sh 'python contrib/upload_docs.py --username=$docsUsername --password=$docsPassword --subroute=speedwagon-uiucpreson build/docs/html apache-ns.library.illinois.edu'
                        }
                    }
                    post{
                        cleanup{
                            cleanWs(
                                deleteDirs: true,
                                patterns: [
                                    [pattern: 'build/', type: 'INCLUDE'],
                                    [pattern: 'dist/', type: 'INCLUDE'],
                                ]
                            )
                        }
                    }
                }
                stage('Deploy Standalone'){
                    when {
                        allOf{
                            equals expected: true, actual: params.DEPLOY_STANDALONE_PACKAGERS
                            anyOf{
                                equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                equals expected: true, actual: params.PACKAGE_STANDALONE_WINDOWS_INSTALLER
                            }
                        }
                        beforeAgent true
                        beforeInput true
                    }
                    input {
                        message 'Upload to Nexus server?'
                        parameters {
                            credentials credentialType: 'com.cloudbees.plugins.credentials.common.StandardCredentials', defaultValue: 'jenkins-nexus', name: 'NEXUS_CREDS', required: true
                            choice(
                                choices: getStandAloneStorageServers(),
                                description: 'Url to upload artifact.',
                                name: 'SERVER_URL'
                            )
                            string defaultValue: "speedwagon_uiuc/${props.version}", description: 'subdirectory to store artifact', name: 'archiveFolder'
                        }
                    }
                    stages{
                        stage('Deploy Installers'){
                            agent any
                            options {
                                skipDefaultCheckout(true)
                            }
                            stages{
                                stage('Include Mac Bundle Installer for Deployment'){
                                    when{
                                        allOf{
                                            equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                            anyOf{
                                                equals expected: true, actual: params.INCLUDE_MACOS_X86_64
                                                equals expected: true, actual: params.INCLUDE_MACOS_ARM

                                            }
                                        }
                                    }
                                    steps {
                                        script{
                                            if(params.INCLUDE_MACOS_X86_64){
                                                unstash 'APPLE_APPLICATION_BUNDLE_X86_64'
                                            }
                                            if(params.INCLUDE_MACOS_ARM){
                                                unstash 'APPLE_APPLICATION_BUNDLE_M1'
                                            }
                                        }
                                    }
                                }
                                stage('Include Windows Installer(s) for Deployment'){
                                    when{
                                        equals expected: true, actual: params.PACKAGE_STANDALONE_WINDOWS_INSTALLER
                                    }
                                    steps {
                                        unstash 'STANDALONE_WINDOWS_INSTALLER'
                                    }
                                }
                                stage('Deploy'){
                                    steps {
                                        unstash 'SPEEDWAGON_DOC_PDF'
                                        deployStandalone('dist/*.msi,dist/*.exe,dist/*.zip,dist/*.tar.gz,dist/docs/*.pdf,dist/*.dmg', "${SERVER_URL}/${archiveFolder}")
                                    }
                                }
                            }
                            post{
                                cleanup{
                                    cleanWs(
                                        deleteDirs: true,
                                        patterns: [
                                            [pattern: 'dist.*', type: 'INCLUDE']
                                        ]
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}