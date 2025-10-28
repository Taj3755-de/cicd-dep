pipeline {
  agent any

  parameters {
    choice(name: 'DEPLOY_ENV', choices: ['staging','production'], description: 'Select deployment environment')
  }

  environment {
    REGISTRY = "172.31.3.134:5000"
    IMAGE_NAME = "nginx-app"
    K8S_MASTER = "rocky@172.31.86.230"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build Docker Image') {
      steps {
        dir('app') {
          sh '''
            echo ">>> Building Docker image..."
            docker build -t ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER} .
          '''
        }
      }
    }

    stage('Trivy Scan') {
      steps {
        sh '''
          echo ">>> Running Trivy image scan..."
          if ! command -v trivy >/dev/null 2>&1; then
            curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh
          fi
          trivy image --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER} || { echo "CRITICAL/HIGH vulnerabilities found"; exit 1; }
        '''
      }
    }

    stage('Push to Registry') {
      steps {
        sh 'docker push ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}'
      }
    }

    stage('Deploy via Helm on K8s Master') {
      steps {
        sshagent(['kube-master-ssh']) {
          sh '''
            echo ">>> Deploying Helm release on K8s..."
            ssh -o StrictHostKeyChecking=no ${K8S_MASTER} "
              mkdir -p ~/my-nginx-app &&
              rm -rf ~/my-nginx-app/helm &&
              mkdir -p ~/my-nginx-app/helm &&
              exit
            "
            scp -o StrictHostKeyChecking=no -r helm/nginx-app ${K8S_MASTER}:~/my-nginx-app/helm/
            ssh -o StrictHostKeyChecking=no ${K8S_MASTER} "
              helm upgrade --install nginx-release ~/my-nginx-app/helm/nginx-app \
                -n ${params.DEPLOY_ENV} \
                -f ~/my-nginx-app/helm/nginx-app/values-${params.DEPLOY_ENV}.yaml \
                --set image.repository=${REGISTRY}/${IMAGE_NAME} \
                --set image.tag=${BUILD_NUMBER}
            "
          '''
        }
      }
    }

    stage('Post-Deploy Check') {
      steps {
        sshagent(['kube-master-ssh']) {
          sh 'ssh -o StrictHostKeyChecking=no ${K8S_MASTER} "/bin/kubectl get pods -n ${params.DEPLOY_ENV} -o wide"'
        }
      }
    }
  }
}
