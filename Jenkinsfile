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

  stage('TruffleHog - Secret Scan') {
  steps {
    sh '''
      echo ">>> Running TruffleHog (Docker) secret scan..."
      docker run --rm -v $(pwd):/repo ghcr.io/trufflesecurity/trufflehog:latest \
        filesystem /repo --fail --json > trufflehog-report.json || {
          echo "❌ Secrets found in repository!";
   
      }
    '''
  }
}

stage('Unit Tests') {
    steps {
        sh '''
        echo ">>> Running unit tests..."
        pip install -r app/requirements.txt pytest pytest-cov
        export PYTHONPATH=$PYTHONPATH:$(pwd)/app
        pytest -v app/tests
        '''
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

 stage('Deploy via Helm (Atomic)') {
    steps {
        sshagent(['kube-master-ssh']) {
            sh '''
            echo ">>> Deploying via Helm (Atomic & Safe Mode)..."
            ssh -o StrictHostKeyChecking=no ${K8S_MASTER} bash -c "'
              mkdir -p /home/rocky/deployments && \
              rm -rf /home/rocky/deployments/py-app && \
              scp -r helm/py-app /home/rocky/deployments/ && \
              helm upgrade --install py-app /home/rocky/deployments/py-app \
                --namespace ${DEPLOY_ENV} \
                --create-namespace \
                --values /home/rocky/deployments/py-app/values-${DEPLOY_ENV}.yaml \
                --set image.repository=${REGISTRY}/${IMAGE_NAME} \
                --set image.tag=${BUILD_NUMBER} \
                --atomic \
                --wait \
                --timeout 5m
            '"
            '''
        }
    }
}

stage('Post Deploy Check') {
  steps {
    sshagent(['kube-master-ssh']) {
      sh """
        echo ">>> Checking deployment status..."
        ssh -o StrictHostKeyChecking=no ${K8S_MASTER} "kubectl get pods -n ${DEPLOY_ENV} -o wide"
      """
    }
  }
}
  }
}
