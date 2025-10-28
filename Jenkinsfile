pipeline {
  agent any

  parameters {
    choice(name: 'DEPLOY_ENV', choices: ['staging','production'], description: 'Select deployment environment')
  }

  environment {
    REGISTRY = "172.31.3.134:5000"
    IMAGE_NAME = "py-app"
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
        echo ">>> Running Trivy scan..."
              trivy image --severity HIGH,CRITICAL --exit-code 1 ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER} || {
          echo "❌ Critical vulnerabilities found! Build failed.";
          exit 1;
        }
        '''
      }
    }

    stage('Push to Registry') {
      steps {
        sh '''
        echo ">>> Pushing Docker image to ${REGISTRY}..."
        docker push ${REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}
        '''
      }
    }

    stage('Debug Workspace') {
  steps {
    sh 'pwd && ls -R'
  }
}

    stage('Deploy via Helm') {
      steps {
        sshagent(['kube-master-ssh']) {
          sh '''
          echo ">>> Deploying via Helm..."
          ssh -o StrictHostKeyChecking=no ${K8S_MASTER} "
            mkdir -p /home/rocky/deployments &&
            rm -rf /home/rocky/deployments/py-app &&
            scp -r helm/py-app /home/rocky/deployments/
          "
          ssh -o StrictHostKeyChecking=no ${K8S_MASTER} "
            helm upgrade --install py-app-release /home/rocky/deployments/py-app \
              -n ${params.DEPLOY_ENV} \
              -f /home/rocky/deployments/py-app/values-${params.DEPLOY_ENV}.yaml \
              --set image.repository=${REGISTRY}/${IMAGE_NAME} \
              --set image.tag=${BUILD_NUMBER}
          "
          '''
        }
      }
    }

    stage('Post-Deployment Check') {
      steps {
        sshagent(['kube-master-ssh']) {
          sh '''
          ssh -o StrictHostKeyChecking=no ${K8S_MASTER} "
            kubectl get pods -n ${params.DEPLOY_ENV} -o wide
          "
          '''
        }
      }
    }
  }
}
