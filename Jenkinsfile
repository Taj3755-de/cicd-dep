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
      echo ">>> Running TruffleHog secret scan..."
      docker run --rm -v $(pwd):/repo ghcr.io/trufflesecurity/trufflehog:latest \
        filesystem /repo --fail --json > trufflehog-report.json || true
         echo "Secrets found in repository!";

    '''
  }
  post {
    always {
      archiveArtifacts artifacts: 'trufflehog-report.json', fingerprint: true
    }
    failure {
      echo "❌ TruffleHog found secrets — failing build!"
    }
  }
}

stage('tfsec - IaC Security Scan') {
  steps {
    sh '''
      echo "Running tfsec scan..."
      
      # Run tfsec with soft-fail so pipeline doesn't stop automatically
      tfsec helm/py-app --format json --out tfsec-report.json --soft-fail
      
      # You can comment out exit 1 if you don't want to fail the build on findings
      if grep -q '"severity":"HIGH"' tfsec-report.json || grep -q '"severity":"CRITICAL"' tfsec-report.json; then
        echo " High or Critical issues detected in tfsec scan!"
        # exit 1   # <-- Uncomment this to fail the pipeline on critical findings
      else
        echo " No high-severity tfsec issues detected."
      fi

      echo "tfsec report generated: tfsec-report.json"
    '''
  }
  post {
    always {
      echo "Archiving tfsec report..."
      archiveArtifacts artifacts: 'tfsec-report.json', fingerprint: true
    }
  }
}


stage('Unit Tests') {
  steps {
    sh '''
      echo ">>> Running unit tests..."
      pip install -r app/requirements.txt pytest pytest-cov
      export PYTHONPATH=$PYTHONPATH:$(pwd)/app
      pytest app/tests --junitxml=pytest-report.xml --cov=app --cov-report=html
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

    
stage('Deploy via Helm (Atomic)') {
    steps {
        sshagent(['kube-master-ssh']) {
            sh '''
            echo ">>> Deploying via Helm (Atomic)..."

            # Save workspace for reference
            WORKSPACE_DIR=$(pwd)
            echo "Current Jenkins workspace: $WORKSPACE_DIR"

            # Copy Helm chart to Kubernetes master
            ssh -o StrictHostKeyChecking=no rocky@172.31.86.230 "mkdir -p /home/rocky/deployments"
            scp -o StrictHostKeyChecking=no -r $WORKSPACE_DIR/helm/py-app rocky@172.31.86.230:/home/rocky/deployments/

            # Deploy using Helm with atomic mode
            ssh -o StrictHostKeyChecking=no rocky@172.31.86.230 "
              helm upgrade --install py-app /home/rocky/deployments/py-app \
                -n ${DEPLOY_ENV} \
                -f /home/rocky/deployments/py-app/values-${DEPLOY_ENV}.yaml \
                --set image.repository=${REGISTRY}/${IMAGE_NAME} \
                --set image.tag=${BUILD_NUMBER} \
            "
            '''
        }
    }
}

    stage('Archive Reports') {
  steps {
    archiveArtifacts artifacts: '''
      trufflehog-report.json,
      tfsec-report.json,
      pytest-report.xml,
      htmlcov/**
    ''', fingerprint: true
    junit 'pytest-report.xml'
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
