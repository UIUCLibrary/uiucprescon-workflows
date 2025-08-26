def createChocolateyConfigFile(configJsonFile, installerPackage, url){
    def deployJsonMetadata = [
        "PackageVersion": readTOML( file: 'pyproject.toml')['project'].version,
        "url": url,
        "sha256": sha256(installerPackage.path),
    ]
    writeJSON( json: deployJsonMetadata, file: configJsonFile, pretty: 2)
}

def makeMacPackage(){
    findFiles(glob: 'dist/*.whl').each{ wheel ->
        withEnv(["WHEEL=${wheel.path}"]){
            sh """
                python3 -m venv venv
                . ./venv/bin/activate
                pip install --disable-pip-version-check uv
                uv export --no-hashes --format requirements-txt --extra gui --no-dev --no-emit-project > requirements-gui.txt
                uvx --python 3.11 --from package_speedwagon@https://github.com/UIUCLibrary/speedwagon_scripts/archive/refs/tags/v0.1.0.tar.gz package_speedwagon $WHEEL -r requirements-gui.txt --app-name=\"$APP_NAME\" --app-bootstrap-script=\"$BOOTSTRAP_SCRIPT\"
                """
        }
    }
}

def deploySingleStandalone(file, url, authentication) {
    script{
        try{
            def encodedUrlFileName = new URI(null, null, file.name, null).toASCIIString()
            def newUrl = "${url}/${encodedUrlFileName}"
            def putResponse = httpRequest authentication: authentication, httpMode: 'PUT', uploadFile: file.path, url: "${newUrl}", wrapAsMultipart: false
            return newUrl
        } catch(Exception e){
            echo "${e}"
            throw e;
        }
    }
}

// def deployStandalone(glob, url) {
//     script{
//         findFiles(glob: glob).each{
//             try{
//                 def encodedUrlFileName = new URI(null, null, it.name, null).toASCIIString()
//                 def putResponse = httpRequest authentication: NEXUS_CREDS, httpMode: 'PUT', uploadFile: it.path, url: "${url}/${encodedUrlFileName}", wrapAsMultipart: false
//                 echo "http request response: ${putResponse.content}"
//                 echo "Deployed ${it} -> SHA256: ${sha256(it.path)}"
//             } catch(Exception e){
//                 echo "${e}"
//                 throw e;
//             }
//         }
//     }
// }

def testPackage(entry){
    if(['linux', 'windows'].contains(entry.OS) && params.containsKey("INCLUDE_${entry.OS}-${entry.ARCHITECTURE}".toUpperCase()) && params["INCLUDE_${entry.OS}-${entry.ARCHITECTURE}".toUpperCase()]){
        docker.image(env.DEFAULT_PYTHON_DOCKER_IMAGE ? env.DEFAULT_PYTHON_DOCKER_IMAGE: 'python')
            .inside(
                isUnix() ?
                '--mount source=python-tmp-uiucpreson_workflows,target=/tmp':
                '--mount type=volume,source=uv_python_install_dir,target=C:\\Users\\ContainerUser\\Documents\\cache\\uvpython \
                 --mount type=volume,source=pipcache,target=C:\\Users\\ContainerUser\\Documents\\cache\\pipcache \
                 --mount type=volume,source=msvc-runtime,target=c:\\msvc_runtime \
                 --mount type=volume,source=uv_cache_dir,target=C:\\Users\\ContainerUser\\Documents\\cache\\uvcache'
            ){
             if(isUnix()){
                withEnv([
                    'PIP_CACHE_DIR=/tmp/pipcache',
                    'UV_TOOL_DIR=/tmp/uvtools',
                    'UV_PYTHON_INSTALL_DIR=/tmp/uvpython',
                    'UV_CACHE_DIR=/tmp/uvcache',
                    "UV_CONFIG_FILE=${createUnixUvConfig()}",
                ]){
                     sh(
                        label: 'Testing with tox',
                        script: """python3 -m venv venv
                                   ./venv/bin/pip install --disable-pip-version-check uv
                                   ./venv/bin/uv python install cpython-${entry.PYTHON_VERSION}
                                   ./venv/bin/uvx --with tox-uv tox --installpkg ${findFiles(glob: entry.PACKAGE_TYPE == 'wheel' ? 'dist/*.whl' : 'dist/*.tar.gz')[0].path} -e py${entry.PYTHON_VERSION.replace('.', '')}
                                """
                    )
                }
             } else {
                withEnv([
                    'PIP_CACHE_DIR=C:\\Users\\ContainerUser\\Documents\\cache\\pipcache',
                    'UV_TOOL_DIR=C:\\Users\\ContainerUser\\Documents\\cache\\uvtools',
                    'UV_PYTHON_INSTALL_DIR=C:\\Users\\ContainerUser\\Documents\\cache\\uvpython',
                    'UV_CACHE_DIR=C:\\Users\\ContainerUser\\Documents\\cache\\uvcache',
                    "UV_CONFIG_FILE=${createWindowUVConfig()}",
                ]){
                    installMSVCRuntime('c:\\msvc_runtime\\')
                    bat(
                        label: 'Testing with tox',
                        script: """python -m venv venv
                                   .\\venv\\Scripts\\pip install --disable-pip-version-check uv
                                   .\\venv\\Scripts\\uv python install cpython-${entry.PYTHON_VERSION}
                                   .\\venv\\Scripts\\uvx --with tox-uv tox --installpkg ${findFiles(glob: entry.PACKAGE_TYPE == 'wheel' ? 'dist/*.whl' : 'dist/*.tar.gz')[0].path} -e py${entry.PYTHON_VERSION.replace('.', '')}
                                """
                    )
                }
             }
        }
    } else {
        if(isUnix()){
            withEnv(["UV_CONFIG_FILE=${createUnixUvConfig()}"]){
                sh(
                    label: 'Testing with tox',
                    script: """python3 -m venv venv
                               ./venv/bin/pip install --disable-pip-version-check uv
                               ./venv/bin/uvx --with tox-uv tox --installpkg ${findFiles(glob: entry.PACKAGE_TYPE == 'wheel' ? 'dist/*.whl' : 'dist/*.tar.gz')[0].path} -e py${entry.PYTHON_VERSION.replace('.', '')}
                            """
                )
            }
        } else {
            withEnv(["UV_CONFIG_FILE=${createWindowUVConfig()}"]){
                bat(
                    label: 'Testing with tox',
                    script: """python -m venv venv
                               .\\venv\\Scripts\\pip install --disable-pip-version-check uv
                               .\\venv\\Scripts\\uv python install cpython-${entry.PYTHON_VERSION}
                               .\\venv\\Scripts\\uvx --with tox-uv tox --installpkg ${findFiles(glob: entry.PACKAGE_TYPE == 'wheel' ? 'dist/*.whl' : 'dist/*.tar.gz')[0].path} -e py${entry.PYTHON_VERSION.replace('.', '')}
                            """
                )
            }
        }
    }
}

def get_sonarqube_unresolved_issues(report_task_file){
    script{

        def props = readProperties  file: report_task_file
        def response = httpRequest url : props['serverUrl'] + "/api/issues/search?componentKeys=" + props['projectKey'] + "&resolved=no"
        def outstandingIssues = readJSON text: response.content
        return outstandingIssues
    }
}

def installMSVCRuntime(cacheLocation){
    def cachedFile = "${cacheLocation}\\vc_redist.x64.exe".replaceAll(/\\\\+/, '\\\\')
    withEnv(
        [
            "CACHED_FILE=${cachedFile}",
            "RUNTIME_DOWNLOAD_URL=https://aka.ms/vs/17/release/vc_redist.x64.exe"
        ]
    ){
        lock("${cachedFile}-${env.NODE_NAME}"){
            powershell(
                label: 'Ensuring vc_redist runtime installer is available',
                script: '''if ([System.IO.File]::Exists("$Env:CACHED_FILE"))
                           {
                                Write-Host 'Found installer'
                           } else {
                                Write-Host 'No installer found'
                                Write-Host 'Downloading runtime'
                                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;Invoke-WebRequest "$Env:RUNTIME_DOWNLOAD_URL" -OutFile "$Env:CACHED_FILE"
                           }
                        '''
            )
        }
        powershell(label: 'Install VC Runtime', script: 'Start-Process -filepath "$Env:CACHED_FILE" -ArgumentList "/install", "/passive", "/norestart" -Passthru | Wait-Process;')
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

def getVersion(){
    node(){
        checkout scm
        return readTOML( file: 'pyproject.toml')['project']['version']
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
def getToxEnvs(){
    try{
        checkout scm
        if(isUnix()){
            withEnv(["UV_CONFIG_FILE=${createUnixUvConfig()}"]){
                sh(script: 'python3 -m venv venv && venv/bin/pip install --disable-pip-version-check uv')
                return sh(
                    label: 'Get tox environments',
                    script: './venv/bin/uvx --quiet --with tox-uv tox list -d --no-desc',
                    returnStdout: true,
                ).trim().split('\n')
            }
        } else{
            withEnv(["UV_CONFIG_FILE=${createWindowUVConfig()}"]){
                bat(script: 'python -m venv venv && venv\\Scripts\\pip install --disable-pip-version-check uv')
                return bat(
                    label: 'Get tox environments',
                    script: '@.\\venv\\Scripts\\uvx --quiet --with tox-uv tox list -d --no-desc',
                    returnStdout: true,
                ).trim().split('\r\n')
            }
        }
    } finally{
        cleanWs(
            patterns: [
                [pattern: 'venv/', type: 'INCLUDE'],
                [pattern: '.tox/', type: 'INCLUDE'],
                [pattern: '**/__pycache__/', type: 'INCLUDE'],
            ]
        )
    }
}

def getLinusToxEnvs(){
    node('docker && linux && x86_64'){
        try{
            docker.image('python').inside('--mount source=python-tmp-uiucpreson_workflows,target=/tmp'){
                return getToxEnvs()
            }
        } finally{
            sh "${tool(name: 'Default', type: 'git')} clean -dfx"
        }
    }
}

def getWindowsToxEnvs(){
    node('docker && windows'){
        checkout scm
        try{
            docker.image(env.DEFAULT_PYTHON_DOCKER_IMAGE ? env.DEFAULT_PYTHON_DOCKER_IMAGE: 'python')
                .inside("\
                    --mount type=volume,source=uv_python_install_dir,target=${env.UV_PYTHON_INSTALL_DIR} \
                    --mount type=volume,source=pipcache,target=${env.PIP_CACHE_DIR} \
                    --mount type=volume,source=uv_cache_dir,target=${env.UV_CACHE_DIR}\
                    "
                ){
                    return getToxEnvs()
                }
        } finally{
            bat "${tool(name: 'Default', type: 'git')} clean -dfx"
        }
    }
}

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


def getMsiInstallerPath(){
    def msiFiles = findFiles(glob: 'dist/*.msi')
    if(msiFiles.size()==0){
        error 'No .msi file found in ./dist/'
    }
    if(msiFiles.size()>1){
        error 'more than one .msi file found ./dist/'
    }
    return msiFiles[0].path
}


def submitToSonarQube(sonarToken, version){
    withEnv([
            "VERSION=${version}",
            "SONAR_TOKEN=${sonarToken}"
        ]
    ){
        withSonarQubeEnv(installationName:'sonarcloud', credentialsId: sonarToken) {
           def sourceInstruction
           if (env.CHANGE_ID){
               sourceInstruction = '-Dsonar.pullrequest.key=$CHANGE_ID -Dsonar.pullrequest.base=$BRANCH_NAME'
           } else{
               sourceInstruction = '-Dsonar.branch.name=$BRANCH_NAME'
           }
           withCredentials([string(credentialsId: sonarToken, variable: 'token')]) {
               sh(
                   label: 'Running Sonar Scanner',
                   script: """. ./venv/bin/activate
                               pysonar -Dsonar.projectVersion=$VERSION -Dsonar.buildString=\"$BUILD_TAG\" ${sourceInstruction} -t \$token
                           """
               )
           }
        }
        timeout(time: 1, unit: 'HOURS') {
           def sonarqube_result = waitForQualityGate(abortPipeline: false)
           if (sonarqube_result.status != 'OK') {
               unstable "SonarQube quality gate: ${sonarqube_result.status}"
           }
           writeJSON file: 'reports/sonar-report.json', json: get_sonarqube_unresolved_issues('.sonar/report-task.txt')
        }
    }
}
def createWindowUVConfig(){
    if(! fileExists('ci/jenkins/scripts/new-uv-global-config.ps1')){
        checkout scm
    }
    return powershell(label: 'Setting up uv.toml config file', script: 'ci/jenkins/scripts/new-uv-global-config.ps1 $env:UV_INDEX_URL $env:UV_EXTRA_INDEX_URL', returnStdout: true).trim()
}

def createUnixUvConfig(){
    return sh(label: 'Setting up uv.toml config file', script: 'sh ci/jenkins/scripts/create_uv_config.sh $UV_INDEX_URL $UV_EXTRA_INDEX_URL', returnStdout: true).trim()
}

def call(){
    library(
        identifier: 'JenkinsPythonHelperLibrary@2024.12.0',
        retriever: modernSCM(
            [
                $class: 'GitSCMSource',
                remote: 'https://github.com/UIUCLibrary/JenkinsPythonHelperLibrary.git',
            ]
        )
    )
    pipeline {
        agent none
        parameters {
            booleanParam(name: 'RUN_CHECKS', defaultValue: true, description: 'Run checks on code')
            booleanParam(name: 'USE_SONARQUBE', defaultValue: true, description: 'Send data test data to SonarQube')
            credentials(name: 'SONARCLOUD_TOKEN', credentialType: 'org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl', defaultValue: 'sonarcloud_token', required: false)
            booleanParam(name: 'TEST_RUN_TOX', defaultValue: false, description: 'Run Tox Tests')
            booleanParam(name: 'BUILD_PACKAGES', defaultValue: false, description: 'Build Packages')
            booleanParam(name: 'INCLUDE_LINUX-ARM64', defaultValue: false, description: 'Include ARM architecture for Linux')
            booleanParam(name: 'INCLUDE_LINUX-X86_64', defaultValue: true, description: 'Include x86_64 architecture for Linux')
            booleanParam(name: 'INCLUDE_MACOS-ARM64', defaultValue: false, description: 'Include ARM(m1) architecture for Mac')
            booleanParam(name: 'INCLUDE_MACOS-X86_64', defaultValue: false, description: 'Include x86_64 architecture for Mac')
            booleanParam(name: 'INCLUDE_WINDOWS-X86_64', defaultValue: true, description: 'Include x86_64 architecture for Windows')
            booleanParam(name: 'TEST_PACKAGES', defaultValue: true, description: 'Test Python packages by installing them and running tests on the installed package')
            booleanParam(name: 'PACKAGE_MAC_OS_STANDALONE_DMG', defaultValue: false, description: 'Create a Apple Application Bundle DMG')
            booleanParam(name: 'PACKAGE_STANDALONE_WINDOWS_INSTALLER', defaultValue: false, description: 'Create a standalone wix based .msi installer')
            booleanParam(name: 'DEPLOY_PYPI', defaultValue: false, description: 'Deploy to pypi')
            booleanParam(name: 'DEPLOY_STANDALONE_PACKAGERS', defaultValue: false, description: 'Deploy standalone packages')
            booleanParam(name: 'DEPLOY_DOCS', defaultValue: false, description: 'Update online documentation')
        }
        stages {
            stage('Build Sphinx Documentation'){
                agent {
                    docker{
                        image 'sphinxdoc/sphinx-latexpdf'
                        label 'linux && docker && x86'
                        args '--mount source=python-tmp-uiucpreson_workflows,target=/tmp'
                    }
                }
                options {
                    retry(conditions: [agent()], count: 2)
                }
                environment{
                    PIP_CACHE_DIR = '/tmp/pipcache'
                    UV_TOOL_DIR = '/tmp/uvtools'
                    UV_PYTHON_INSTALL_DIR = '/tmp/uvpython'
                    UV_CACHE_DIR = '/tmp/uvcache'
                    UV_PYTHON = '3.11'
                    UV_CONFIG_FILE=createUnixUvConfig()
                }
                steps {
                    catchError(buildResult: 'UNSTABLE', message: 'Sphinx has warnings', stageResult: 'UNSTABLE') {
                        sh(label: 'Build docs in html and Latex formats',
                           script:'''python3 -m venv venv
                              trap "rm -rf venv" EXIT
                              . ./venv/bin/activate
                              pip install --disable-pip-version-check uv
                              uv sync --active --locked --group docs
                              sphinx-build -W --keep-going -b html -d build/docs/.doctrees -w logs/build_sphinx_html.log docs build/docs/html
                              sphinx-build -W --keep-going -b latex -d build/docs/.doctrees docs build/docs/latex
                              ''')
                        script{
                            def props = readTOML( file: 'pyproject.toml')['project']
                            zip archive: true, dir: 'build/docs/html', glob: '', zipFile: "dist/${props.name}-${props.version}.doc.zip"
                            stash includes: 'dist/*.doc.zip,build/docs/html/**', name: 'DOCS_ARCHIVE'
                        }
                        sh(label: 'Building PDF docs',
                           script: '''make -C build/docs/latex
                                        mkdir -p dist/docs
                                        mv build/docs/latex/*.pdf dist/docs/
                                        '''
                        )
                        stash includes: 'dist/docs/*.pdf', name: 'SPEEDWAGON_DOC_PDF'
                        archiveArtifacts artifacts: 'dist/docs/*.pdf'
                    }
                }
                post{
                    always{
                        recordIssues(tools: [sphinxBuild(pattern: 'logs/build_sphinx_html.log')])
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
                            docker{
                                image 'python'
                                label 'docker && linux && x86_64' // needed for pysonar-scanner which is x86_64 only as of 0.2.0.520
                                args '--mount source=python-tmp-uiucpreson_workflows,target=/tmp'
                            }
                        }
                        environment{
                            PIP_CACHE_DIR='/tmp/pipcache'
                            UV_TOOL_DIR='/tmp/uvtools'
                            UV_PYTHON_INSTALL_DIR='/tmp/uvpython'
                            UV_CACHE_DIR='/tmp/uvcache'
                            UV_PYTHON='3.11'
                            QT_QPA_PLATFORM='offscreen'
                            UV_CONFIG_FILE=createUnixUvConfig()
                        }
                        options {
                            retry(conditions: [agent()], count: 2)
                        }
                        stages{
                            stage('Test') {
                                stages{
                                    stage('Configuring Testing Environment'){
                                        steps{
                                            sh(
                                                label: 'Create virtual environment',
                                                script: '''python3 -m venv bootstrap_uv
                                                           bootstrap_uv/bin/pip install --disable-pip-version-check uv
                                                           bootstrap_uv/bin/uv venv venv
                                                           . ./venv/bin/activate
                                                           bootstrap_uv/bin/uv sync --active --locked --group ci --extra gui
                                                           bootstrap_uv/bin/uv pip install --disable-pip-version-check uv
                                                           rm -rf bootstrap_uv
                                                           '''
                                                       )
                                            sh(
                                                label: 'Creating logging and report directories',
                                                script: '''mkdir -p logs
                                                           mkdir -p reports
                                                        '''
                                            )
                                        }
                                    }
                                    stage('Run Tests'){
                                        parallel {
                                            stage('Run PyTest Unit Tests'){
                                                steps{
                                                    catchError(buildResult: 'UNSTABLE', message: 'Did not pass all pytest tests', stageResult: 'UNSTABLE') {
                                                        sh(
                                                            script: '''. ./venv/bin/activate
                                                                       PYTHONFAULTHANDLER=1 coverage run --parallel-mode --source=speedwagon_uiucprescon -m pytest --junitxml=./reports/tests/pytest/pytest-junit.xml --capture=no
                                                                   '''
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
                                                    catchError(buildResult: 'SUCCESS', message: 'uv-secure found issues', stageResult: 'UNSTABLE') {
                                                        sh './venv/bin/uvx uv-secure --cache-path=/tmp/cache/uv-secure uv.lock'
                                                    }
                                                }
                                            }
                                            stage('Run Doctest Tests'){
                                                steps {
                                                    sh(
                                                        label: 'Running Doctest Tests',
                                                        script: '''. ./venv/bin/activate
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
                                                               script: '''. ./venv/bin/activate
                                                                          mypy -p speedwagon_uiucprescon --html-report reports/mypy/html
                                                                       '''
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
                                                            script: '''. ./venv/bin/activate
                                                                       pylint speedwagon_uiucprescon -r n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > reports/pylint.txt
                                                                    '''
                                                        )
                                                    }
                                                    sh(
                                                        label: 'Running pylint for sonarqube',
                                                        returnStatus: true,
                                                        script: '''. ./venv/bin/activate
                                                                   pylint speedwagon_uiucprescon -r n --msg-template="{path}:{module}:{line}: [{msg_id}({symbol}), {obj}] {msg}" | tee reports/pylint_issues.txt
                                                                ''',
                                                    )
                                                }
                                                post{
                                                    always{
                                                        recordIssues(tools: [pyLint(pattern: 'reports/pylint.txt')])
                                                    }
                                                }
                                            }
                                            stage('Run Flake8 Static Analysis') {
                                                steps{
                                                    catchError(buildResult: 'SUCCESS', message: 'Flake8 found issues', stageResult: 'UNSTABLE') {
                                                        sh script: '''. ./venv/bin/activate
                                                                   flake8 speedwagon_uiucprescon -j 1 --tee --output-file=logs/flake8.log
                                                                   '''
                                                    }
                                                    stash includes: 'logs/flake8.log', name: 'FLAKE8_REPORT'
                                                }
                                                post {
                                                    always {
                                                          recordIssues(tools: [flake8(pattern: 'logs/flake8.log')])
                                                    }
                                                }
                                            }
                                            stage('pyDocStyle'){
                                                steps{
                                                    catchError(buildResult: 'SUCCESS', message: 'Did not pass all pyDocStyle tests', stageResult: 'UNSTABLE') {
                                                        sh(
                                                            label: 'Run pydocstyle',
                                                            script: '''. ./venv/bin/activate
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
                                                sh '''. ./venv/bin/activate
                                                   coverage combine && coverage xml -o reports/coverage.xml && coverage html -d reports/coverage
                                                   '''
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
                                environment{
                                    VERSION="${readTOML( file: 'pyproject.toml')['project'].version}"
                                    SONAR_USER_HOME='/tmp/sonar'
                                }
                                steps{
                                    submitToSonarQube(params.SONARCLOUD_TOKEN, env.VERSION)
                                }
                                post {
                                    always{
                                        milestone ordinal: 1, label: 'sonarcloud'
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
                        parallel{
                            stage('Linux'){
                                when{
                                    expression {return nodesByLabel('linux && docker && x86').size() > 0}
                                }
                                environment{
                                    PIP_CACHE_DIR='/tmp/pipcache'
                                    UV_TOOL_DIR='/tmp/uvtools'
                                    UV_PYTHON_INSTALL_DIR='/tmp/uvpython'
                                    UV_CACHE_DIR='/tmp/uvcache'
                                    QT_QPA_PLATFORM='offscreen'
                                }
                                steps{
                                    script{
                                        parallel(
                                            getLinusToxEnvs().collectEntries{toxEnv ->
                                                def version = toxEnv.replaceAll(/py(\d)(\d+).*/, '$1.$2')
                                                [
                                                    "Tox Environment: ${toxEnv}",
                                                    {
                                                        node('docker && linux && x86_64'){
                                                            checkout scm
                                                            def retryTimes = 1
                                                            def image
                                                            retry(retryTimes){
                                                                image = docker.build(UUID.randomUUID().toString(), '-f ci/docker/linux/jenkins/Dockerfile --build-arg UV_INDEX_URL --build-arg UV_EXTRA_INDEX_URL .')
                                                            }
                                                                try{
                                                                    withEnv(["UV_CONFIG_FILE=${createUnixUvConfig()}"]){
                                                                        image.inside('--mount source=python-tmp-uiucpreson_workflows,target=/tmp'){
                                                                            retry(retryTimes){
                                                                                try{
                                                                                    sh( label: 'Running Tox',
                                                                                        script: """python3 -m venv venv && venv/bin/pip install --disable-pip-version-check uv
                                                                                                   trap "rm -rf ./venv" EXIT
                                                                                                   ./venv/bin/uv python install cpython-${version}
                                                                                                   trap "rm -rf ./venv && rm -rf .tox" EXIT
                                                                                                   ./venv/bin/uvx -p ${version} --with tox-uv tox run --runner uv-venv-lock-runner -e ${toxEnv}
                                                                                                """
                                                                                        )
                                                                                } catch (e){
                                                                                    cleanWs(
                                                                                        patterns: [
                                                                                            [pattern: 'venv/', type: 'INCLUDE'],
                                                                                            [pattern: '.tox', type: 'INCLUDE'],
                                                                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                                                                        ]
                                                                                    )
                                                                                    throw e
                                                                                }
                                                                            }
                                                                        }
                                                                    }
                                                                } finally {
                                                                    sh "${tool(name: 'Default', type: 'git')} clean -dfx"
                                                            }
                                                        }
                                                    }
                                                ]
                                            }
                                        )
                                    }
                                }
                            }
                            stage('Windows'){
                                when{
                                    expression {return nodesByLabel('windows && docker && x86').size() > 0}
                                }
                                environment{
                                    PIP_CACHE_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\pipcache'
                                    UV_TOOL_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\uvtools'
                                    UV_PYTHON_INSTALL_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\uvpython'
                                    UV_CACHE_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\uvcache'
                                    VC_RUNTIME_INSTALLER_LOCATION='c:\\msvc_runtime'
                                }
                                steps{
                                    script{
                                        parallel(
                                            getWindowsToxEnvs().collectEntries{toxEnv ->
                                                def version = toxEnv.replaceAll(/py(\d)(\d+).*/, '$1.$2')
                                                [
                                                    "Tox Environment: ${toxEnv}",
                                                    {
                                                        node('docker && windows'){
                                                            retry(3){
                                                                try{
                                                                    withEnv(
                                                                        [
                                                                            "PYTHON_VERSION=${version}",
                                                                            "TOX_ENV=${toxEnv}",
                                                                            "UV_CONFIG_FILE=${createWindowUVConfig()}"
                                                                        ]
                                                                    ){
                                                                        checkout scm
                                                                        try{
                                                                            docker.image(env.DEFAULT_PYTHON_DOCKER_IMAGE ? env.DEFAULT_PYTHON_DOCKER_IMAGE: 'python')
                                                                                .inside("\
                                                                                    --mount type=volume,source=uv_python_install_dir,target=${env.UV_PYTHON_INSTALL_DIR} \
                                                                                    --mount type=volume,source=msvc-runtime,target=${env.VC_RUNTIME_INSTALLER_LOCATION} \
                                                                                    --mount type=volume,source=pipcache,target=${env.PIP_CACHE_DIR} \
                                                                                    --mount type=volume,source=uv_cache_dir,target=${env.UV_CACHE_DIR}\
                                                                                    "
                                                                                ){
                                                                                installMSVCRuntime(env.VC_RUNTIME_INSTALLER_LOCATION)
                                                                                bat(label: 'Running Tox',
                                                                                    script: '''python -m venv venv && venv\\Scripts\\pip install --disable-pip-version-check uv
                                                                                               venv\\Scripts\\uv python install cpython-%PYTHON_VERSION%
                                                                                               venv\\Scripts\\uvx --python %PYTHON_VERSION% --with tox-uv tox run --runner uv-venv-lock-runner -vv
                                                                                               rmdir /s/q venv
                                                                                            '''
                                                                                )
                                                                            }
                                                                        } finally {
                                                                            bat "${tool(name: 'Default', type: 'git')} clean -dfx"
                                                                        }
                                                                    }
                                                                } finally{
                                                                    cleanWs(
                                                                        patterns: [
                                                                            [pattern: 'venv/', type: 'INCLUDE'],
                                                                            [pattern: '.tox/', type: 'INCLUDE'],
                                                                            [pattern: '**/__pycache__/', type: 'INCLUDE'],
                                                                        ]
                                                                    )
                                                                }
                                                            }
                                                        }
                                                    }
                                                ]
                                            }
                                        )
                                    }
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
                                        args '--mount source=python-tmp-uiucpreson_workflows,target=/tmp'
                                      }
                                }
                                environment{
                                    PIP_CACHE_DIR='/tmp/pipcache'
                                    UV_CACHE_DIR='/tmp/uvcache'
                                }
                                options {
                                    timeout(5)
                                }
                                steps{
                                    sh(
                                        label: 'Package',
                                        script: '''python3 -m venv venv && venv/bin/pip install --disable-pip-version-check uv
                                                   trap "rm -rf venv" EXIT
                                                   . ./venv/bin/activate
                                                   uv build
                                                '''
                                    )
                                    stash includes: 'dist/*.whl,dist/*.tar.gz,dist/*.zip', name: 'PYTHON_PACKAGES'
                                }
                                post{
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
                                stages{
                                    stage('Twine Check'){
                                        agent{
                                            docker{
                                                image 'python'
                                                label 'linux && docker'
                                                args '--mount source=python-tmp-uiucpreson_workflows,target=/tmp'
                                            }
                                        }
                                        environment{
                                            UV_TOOL_DIR='/tmp/uvtools'
                                            UV_CACHE_DIR='/tmp/uvcache'
                                        }
                                        steps{
                                            catchError(buildResult: 'UNSTABLE', message: 'twine check found issues', stageResult: 'UNSTABLE') {
                                                unstash 'PYTHON_PACKAGES'
                                                sh(
                                                    label: 'Checking with twine check',
                                                    script: '''python3 -m venv venv && venv/bin/pip install --disable-pip-version-check uv
                                                               trap "rm -rf venv" EXIT
                                                               . ./venv/bin/activate
                                                               uv sync --active --locked --group ci
                                                               twine check --strict  dist/*
                                                            '''
                                                )
                                            }
                                        }
                                    }
                                    stage('Package Matrix'){
                                        steps{
                                            customMatrix(
                                                axes: [
                                                    [
                                                        name: 'PYTHON_VERSION',
                                                        values: ['3.9', '3.10', '3.11', '3.12','3.13']
                                                    ],
                                                    [
                                                        name: 'OS',
                                                        values: ['linux','macos','windows']
                                                    ],
                                                    [
                                                        name: 'ARCHITECTURE',
                                                        values: ['x86_64', 'arm64']
                                                    ],
                                                    [
                                                        name: 'PACKAGE_TYPE',
                                                        values: ['wheel', 'sdist'],
                                                    ]
                                                ],
                                                excludes: [
                                                    [
                                                        [
                                                            name: 'OS',
                                                            values: 'windows'
                                                        ],
                                                        [
                                                            name: 'ARCHITECTURE',
                                                            values: 'arm64',
                                                        ]
                                                    ]
                                                ],
                                                when: {entry -> "INCLUDE_${entry.OS}-${entry.ARCHITECTURE}".toUpperCase() && params["INCLUDE_${entry.OS}-${entry.ARCHITECTURE}".toUpperCase()]},
                                                stages: [
                                                    { entry ->
                                                        stage('Test Package') {
                                                            retry(3){
                                                                node("${entry.OS} && ${entry.ARCHITECTURE} ${['linux', 'windows'].contains(entry.OS) ? '&& docker': ''}"){
                                                                    try{
                                                                        checkout scm
                                                                        unstash 'PYTHON_PACKAGES'
                                                                        testPackage(entry)
                                                                    } finally{
                                                                        if(isUnix()){
                                                                            sh "${tool(name: 'Default', type: 'git')} clean -dfx"
                                                                        } else {
                                                                            bat "${tool(name: 'Default', type: 'git')} clean -dfx"
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                ]
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                    stage('End-user packages'){
                        environment {
                            APP_NAME="Speedwagon (UIUC Prescon Edition)"
                            BOOTSTRAP_SCRIPT="./contrib/speedwagon_bootstrap.py"
                        }
                        parallel{
                            stage('Mac Application Bundle x86_64'){
                                agent{
                                    label 'mac && python3.11 && x86_64'
                                }
                                when{
                                    allOf{
                                        equals expected: true, actual: params['INCLUDE_MACOS-X86_64']
                                        equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                        expression {return nodesByLabel('mac && python3.11 && x86_64').size() > 0}
                                    }
                                    beforeInput true
                                }
                                steps{
                                    unstash 'PYTHON_PACKAGES'
                                    script{
                                        makeMacPackage()
                                    }
                                    archiveArtifacts artifacts: 'dist/*.dmg', fingerprint: true
                                    stash includes: 'dist/*.dmg', name: 'APPLE_APPLICATION_BUNDLE_X86_64'
                                }
                                post{
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
                                        equals expected: true, actual: params['INCLUDE_MACOS-ARM64']
                                        equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
                                        expression {return nodesByLabel('mac && python3.11 && arm64').size() > 0}
                                    }
                                    beforeInput true
                                }
                                steps{
                                    unstash 'PYTHON_PACKAGES'
                                    script{
                                        makeMacPackage()
                                    }
                                    archiveArtifacts artifacts: 'dist/*.dmg', fingerprint: true
                                    stash includes: 'dist/*.dmg', name: 'APPLE_APPLICATION_BUNDLE_M1'
                                }
                                post{
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
                                when{
                                    equals expected: true, actual: params.PACKAGE_STANDALONE_WINDOWS_INSTALLER
                                }
                                environment{
                                  PIP_CACHE_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\pipcache'
                                  UV_TOOL_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\uvtools'
                                  UV_PYTHON_INSTALL_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\uvpython'
                                  UV_CACHE_DIR='C:\\Users\\ContainerUser\\Documents\\cache\\uvcache'
                                  VC_RUNTIME_INSTALLER_LOCATION='c:\\msvc_runtime'
                                }
                                stages{
                                    stage('Create .msi Installer'){
                                        agent {
                                           docker {
                                               image 'python'
                                               label 'windows && x86_64 && docker'
                                               args " \
                                                    --mount type=volume,source=uv_python_install_dir,target=${env.UV_PYTHON_INSTALL_DIR} \
                                                    --mount type=volume,source=pipcache,target=${env.PIP_CACHE_DIR} \
                                                    --mount type=volume,source=uv_cache_dir,target=${env.UV_CACHE_DIR} \
                                                    --mount type=volume,source=msvc-runtime,target=${env.VC_RUNTIME_INSTALLER_LOCATION} \
                                                    "
                                           }
                                        }
                                        environment{
                                            UV_CONFIG_FILE = createWindowUVConfig()
                                        }
                                        steps{
                                            unstash 'PYTHON_PACKAGES'
                                            script{
                                                powershell(
                                                    label:'Get WiX Toolset',
                                                    script: '''Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.208 -Force
                                                               Register-PackageSource -Name MyNuGet -Location https://www.nuget.org/api/v2 -ProviderName NuGet
                                                               Install-Package -Name wix -Source MyNuGet -Force -ExcludeVersion -RequiredVersion 3.11.2 -Destination .
                                                           '''
                                               )
                                                findFiles(glob: 'dist/*.whl').each{
                                                    withEnv(["WHEEL=${it.path}"]){
                                                        powershell(
                                                            label: 'Create standalone windows version',
                                                            script: '''python -m pip install --disable-pip-version-check uv
                                                                       $env:Path += ";$(Resolve-Path('.\\WiX\\tools\\'))"
                                                                       Write-Host "APP_NAME = $Env:APP_NAME"
                                                                       uv export --no-hashes --format requirements-txt --extra gui --no-dev --no-emit-project > requirements-gui.txt
                                                                       uvx --with-requirements requirements-gui.txt --python 3.11 --from package_speedwagon@https://github.com/UIUCLibrary/speedwagon_scripts/archive/refs/tags/v0.1.0.tar.gz package_speedwagon $Env:WHEEL -r requirements-gui.txt --app-name="$Env:APP_NAME" --app-bootstrap-script="$Env:BOOTSTRAP_SCRIPT"
                                                                    '''
                                                        )
                                                    }
                                                }
                                            }
                                            archiveArtifacts artifacts: 'dist/*.msi', fingerprint: true
                                            stash includes: 'dist/*.msi', name: 'STANDALONE_WINDOWS_X86_64_INSTALLER'
                                        }
                                        post{
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
                                    stage('Test .msi Installer'){
                                        agent {
                                            docker {
                                                args '-u ContainerAdministrator'
                                                image 'mcr.microsoft.com/windows/servercore:ltsc2022'
                                                label 'windows && docker && x86_64'
                                            }
                                        }
                                        options {
                                            skipDefaultCheckout true
                                        }
                                        stages{
                                            stage('Checkout Installer'){
                                                steps{
                                                    unstash 'STANDALONE_WINDOWS_X86_64_INSTALLER'
                                                }
                                            }
                                            stage('Install msi file'){
                                                environment {
                                                    MSI_INSTALLER = getMsiInstallerPath()
                                                }
                                                steps{
                                                    powershell(
                                                        label: 'Installing msi file',
                                                        script: '''[void](New-Item -ItemType Directory -Force -Path logs)
                                                                   Write-Host "Installing $Env:MSI_INSTALLER"
                                                                   msiexec /i $Env:MSI_INSTALLER /qn /norestart /L*v! logs\\msiexec.log
                                                                   '''
                                                    )
                                                    powershell(
                                                        label: 'Show installed applications',
                                                        script: 'Get-WmiObject -Class Win32_Product'
                                                    )
                                                }
                                                post{
                                                    always{
                                                        archiveArtifacts artifacts: 'logs/msiexec.log'
                                                    }
                                                }
                                            }
                                            stage('Verify Installed'){
                                                steps{
                                                    checkout scm
                                                    powershell('./contrib/ensure_installed_property.ps1')
                                                }
                                            }
                                            stage('Uninstall'){
                                                steps{
                                                    powershell(
                                                        label: 'Uninstall',
                                                        script: '''$app = Get-WmiObject -Class Win32_Product -Filter "Name = \"\"$Env:APP_NAME\"\""
                                                                   Write-Host "Uninstalling $app"
                                                                   $app.Uninstall()
                                                                   Get-WmiObject -Class Win32_Product
                                                                '''
                                                   )
                                                   powershell('./contrib/ensure_uninstalled.ps1 --StartMenuShortCutRemoved')
                                                }
                                            }
                                        }
                                        post{
                                            cleanup{
                                                cleanWs(
                                                    deleteDirs: true,
                                                    patterns: [
                                                        [pattern: 'dist/', type: 'INCLUDE'],
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
                stages {
                    stage('Deploy to pypi') {
                        environment{
                            PIP_CACHE_DIR='/tmp/pipcache'
                            UV_TOOL_DIR='/tmp/uvtools'
                            UV_PYTHON_INSTALL_DIR='/tmp/uvpython'
                            UV_CACHE_DIR='/tmp/uvcache'
                        }
                        agent {
                            docker{
                                image 'python'
                                label 'docker && linux && x86_64'
                                args '--mount source=python-tmp-uiucpreson_workflows,target=/tmp'
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
                            withEnv(["TWINE_REPOSITORY_URL=${SERVER_URL}"]){
                                withCredentials(
                                    [
                                        usernamePassword(
                                            credentialsId: 'jenkins-nexus',
                                            passwordVariable: 'TWINE_PASSWORD',
                                            usernameVariable: 'TWINE_USERNAME'
                                        )
                                    ]
                                ){
                                    sh(
                                        label: 'Uploading to pypi',
                                        script: '''python3 -m venv venv
                                                   trap "rm -rf venv" EXIT
                                                   . ./venv/bin/activate
                                                   pip install --disable-pip-version-check uv
                                                   uv sync --active --locked --group ci
                                                   twine upload --disable-progress-bar --non-interactive dist/*
                                                '''
                                    )
                                }
                            }
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
                         environment{
                            PIP_CACHE_DIR='/tmp/pipcache'
                            UV_TOOL_DIR='/tmp/uvtools'
                            UV_PYTHON_INSTALL_DIR='/tmp/uvpython'
                            UV_CACHE_DIR='/tmp/uvcache'
                        }
                        agent {
                            docker{
                                image 'python'
                                label 'docker && linux'
                                args '--mount source=python-tmp-uiucpreson_workflows,target=/tmp'
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
                                string defaultValue: "speedwagon_uiuc/${getVersion()}", description: 'subdirectory to store artifact', name: 'archiveFolder'
                            }
                        }
                        parallel{
                            stage('Deploy Standalone Applications: Windows x86_64'){
                                agent any
                                when{
                                    equals expected: true, actual: params.PACKAGE_STANDALONE_WINDOWS_INSTALLER
                                    beforeAgent true
                                }
                                environment{
                                    GENERATED_CHOCOLATEY_CONFIG_FILE='dist/chocolatey/config.json'
                                }
                                steps{
                                    script{
                                        unstash 'STANDALONE_WINDOWS_X86_64_INSTALLER'
                                        def deploymentFile = findFiles(glob: 'dist/*.msi')[0]
                                        def deployedUrl = deploySingleStandalone(deploymentFile, "${SERVER_URL}/${archiveFolder}", NEXUS_CREDS)
                                        createChocolateyConfigFile(env.GENERATED_CHOCOLATEY_CONFIG_FILE, deploymentFile, deployedUrl)
                                        archiveArtifacts artifacts: env.GENERATED_CHOCOLATEY_CONFIG_FILE
                                        echo "Deployed ${deploymentFile} to ${deployedUrl} -> SHA256: ${sha256(deploymentFile.path)}"
                                    }
                                }
                                post{
                                    success{
                                        echo "Use ${env.GENERATED_CHOCOLATEY_CONFIG_FILE} for deploying to Chocolatey with https://github.com/UIUCLibrary/chocolatey-hosted-public.git. Found in the artifacts for this build."
                                        echo "${readFile(env.GENERATED_CHOCOLATEY_CONFIG_FILE)}"
                                    }
                                }
                            }
                            stage('Deploy Standalone Applications: MacOS ARM64'){
                                agent any
                                when{
                                    equals expected: true, actual: params['INCLUDE_MACOS-ARM64']
                                    beforeAgent true
                                }
                                steps{
                                    script{
                                        unstash 'APPLE_APPLICATION_BUNDLE_M1'
                                        def deploymentFile = findFiles(glob: 'dist/*.dmg')[0]
                                        def deployedUrl = deploySingleStandalone(deploymentFile, "${SERVER_URL}/${archiveFolder}", NEXUS_CREDS)
                                        echo "Deployed ${deploymentFile} to ${deployedUrl} -> SHA256: ${sha256(deploymentFile.path)}"
                                    }
                                }
                            }
                            stage('Deploy Standalone Applications: MacOS X86_64'){
                                agent any
                                when{
                                    equals expected: true, actual: params['INCLUDE_MACOS-X86_64']
                                    beforeAgent true
                                }
                                steps{
                                    script{
                                        unstash 'APPLE_APPLICATION_BUNDLE_X86_64'
                                        def deploymentFile = findFiles(glob: 'dist/*.dmg')[0]
                                        def deployedUrl = deploySingleStandalone(deploymentFile, "${SERVER_URL}/${archiveFolder}", NEXUS_CREDS)
                                        echo "Deployed ${deploymentFile} to ${deployedUrl} -> SHA256: ${sha256(deploymentFile.path)}"
                                    }
                                }
                            }
                            stage('Deploy Standalone Applications: Documentation'){
                                agent any
                                steps{
                                    script{
                                        unstash 'SPEEDWAGON_DOC_PDF'
                                        def deploymentFile = findFiles(glob: 'dist/docs/*.pdf')[0]
                                        def deployedUrl = deploySingleStandalone(deploymentFile, "${SERVER_URL}/${archiveFolder}", NEXUS_CREDS)
                                        echo "Deployed ${deploymentFile} to ${deployedUrl} -> SHA256: ${sha256(deploymentFile.path)}"
                                    }
                                }
                            }
                        }
//                         stages{
//                             stage('Deploy Installers'){
//                                 agent any
//                                 options {
//                                     skipDefaultCheckout(true)
//                                 }
//                                 stages{
//                                     stage('Include Mac Bundle Installer for Deployment'){
//                                         when{
//                                             allOf{
//                                                 equals expected: true, actual: params.PACKAGE_MAC_OS_STANDALONE_DMG
//                                                 anyOf{
//                                                     equals expected: true, actual: params['INCLUDE_MACOS-X86_64']
//                                                     equals expected: true, actual: params['INCLUDE_MACOS-ARM64']
//
//                                                 }
//                                             }
//                                         }
//                                         steps {
//                                             script{
//                                                 if(params['INCLUDE_MACOS-X86_64']){
//                                                     unstash 'APPLE_APPLICATION_BUNDLE_X86_64'
//                                                 }
//                                                 if(params['INCLUDE_MACOS-ARM64']){
//                                                     unstash 'APPLE_APPLICATION_BUNDLE_M1'
//                                                 }
//                                             }
//                                         }
//                                     }
//                                     stage('Include Windows Installer(s) for Deployment'){
//                                         when{
//                                             equals expected: true, actual: params.PACKAGE_STANDALONE_WINDOWS_INSTALLER
//                                         }
//                                         steps {
//                                             unstash 'STANDALONE_WINDOWS_X86_64_INSTALLER'
//                                         }
//                                     }
//                                     stage('Deploy'){
//                                         steps {
//                                             unstash 'SPEEDWAGON_DOC_PDF'
//                                             deployStandalone('dist/*.msi,dist/*.exe,dist/*.zip,dist/*.tar.gz,dist/docs/*.pdf,dist/*.dmg', "${SERVER_URL}/${archiveFolder}")
//                                         }
//                                     }
//                                 }
//                                 post{
//                                     cleanup{
//                                         cleanWs(
//                                             deleteDirs: true,
//                                             patterns: [
//                                                 [pattern: 'dist.*', type: 'INCLUDE']
//                                             ]
//                                         )
//                                     }
//                                 }
//                             }
//                         }
                    }
                }
            }
        }
    }}