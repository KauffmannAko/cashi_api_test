pipeline {
  agent any

  options {
    timestamps()
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Start Services') {
      steps {
        sh 'mkdir -p artifacts/allure-results artifacts/logs artifacts/allure-reports'
        sh 'docker compose up -d mockserver allure'
      }
    }

    stage('Run API Tests') {
      steps {
        sh 'docker compose run --rm tests'
      }
    }
  }

  post {
    always {
      sh 'docker compose logs mockserver > artifacts/logs/mockserver.log || true'
      archiveArtifacts artifacts: 'artifacts/**/*', allowEmptyArchive: true
      script {
        if (fileExists('artifacts/allure-results')) {
          try {
            allure includeProperties: false, jdk: '', results: [[path: 'artifacts/allure-results']]
          } catch (Exception ex) {
            echo "Allure plugin not available or failed: ${ex.getMessage()}"
          }
        }
      }
      sh 'docker compose down || true'
    }
  }
}
