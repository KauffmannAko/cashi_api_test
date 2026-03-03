stage('Run Performance Tests') {
  steps {
    sh 'mkdir -p artifacts/performance artifacts/logs'
    sh 'docker compose up -d mockserver'
    sh '''
      docker compose --profile performance run --rm \
        -e HEADLESS=true \
        -e USERS=10000 \
        -e SPAWN_RATE=500 \
        -e RUN_TIME=5m \
        -e BASE_URL=http://mockserver:1080 \
        -e AUTH_TOKEN=$AUTH_TOKEN \
        locust
    '''
  }
  post {
    always {
      sh 'docker compose logs locust > artifacts/logs/locust.log || true'
      archiveArtifacts artifacts: 'artifacts/performance/**/*,artifacts/logs/locust.log', allowEmptyArchive: true
    }
  }
}
