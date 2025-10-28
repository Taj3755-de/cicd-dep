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
        dir('app') {
          sh '''
            echo ">>> Running Python unit tests..."
            python3 -m venv venv
            . venv/bin/activate
            pip install -r requirements.txt
            pytest --maxfail=1 --disable-warnings -q || { echo "❌ Unit tests failed!"; exit 1; }
          '''
        }
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
        echo ">>> Copying Helm chart to K8s Master..."
        scp -o StrictHostKeyChecking=no -r helm/py-app ${K8S_MASTER}:/home/rocky/deployments/

        echo ">>> Deploying via Helm..."
        ssh -o StrictHostKeyChecking=no ${K8S_MASTER} "
          helm upgrade --install py-app /home/rocky/deployments/py-app \
            -n ${DEPLOY_ENV} \
            -f /home/rocky/deployments/py-app/values-${DEPLOY_ENV}.yaml \
            --set image.repository=${REGISTRY}/${IMAGE_NAME} \
            --set image.tag=${BUILD_NUMBER}
        "
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
