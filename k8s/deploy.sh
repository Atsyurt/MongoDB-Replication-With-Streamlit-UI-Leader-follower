#!/bin/bash

set -e

echo "================================================"
echo "MongoDB Replica Set Kubernetes Deployment"
echo "================================================"
echo ""

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Namespace oluştur
echo -e "${YELLOW}1. Namespace oluşturuluyor...${NC}"
kubectl apply -f namespace.yaml
echo -e "${GREEN}✓ Namespace oluşturuldu${NC}"
echo ""

# 2. MongoDB StatefulSet deploy et
echo -e "${YELLOW}2. MongoDB StatefulSet deploy ediliyor...${NC}"
kubectl apply -f mongodb-statefulset.yaml
echo -e "${GREEN}✓ StatefulSet oluşturuldu${NC}"
echo ""

# 3. Pod'ların hazır olmasını bekle
echo -e "${YELLOW}3. MongoDB pod'larının hazır olması bekleniyor...${NC}"
kubectl wait --for=condition=ready pod -l app=mongodb -n mongodb-replica --timeout=300s
echo -e "${GREEN}✓ Tüm pod'lar hazır${NC}"
echo ""

# 4. Replica set'i başlat
echo -e "${YELLOW}4. Replica set başlatılıyor...${NC}"
kubectl apply -f mongodb-init-job.yaml
echo -e "${GREEN}✓ Init job başlatıldı${NC}"
echo ""

# 5. Job'ın tamamlanmasını bekle
echo -e "${YELLOW}5. Init job'ın tamamlanması bekleniyor...${NC}"
kubectl wait --for=condition=complete job/mongodb-init -n mongodb-replica --timeout=120s
echo -e "${GREEN}✓ Replica set başarıyla başlatıldı${NC}"
echo ""

# 6. Replica set durumunu kontrol et
echo -e "${YELLOW}6. Replica set durumu kontrol ediliyor...${NC}"
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "rs.status()" --quiet | grep -E "name|stateStr"
echo ""

# 7. Streamlit deploy et (opsiyonel)
read -p "Streamlit uygulamasını da deploy etmek istiyor musunuz? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${YELLOW}7. Streamlit uygulaması deploy ediliyor...${NC}"
    
    # Docker image kontrolü
    read -p "Docker image'ınızı push ettiniz mi? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        kubectl apply -f streamlit-deployment.yaml
        kubectl apply -f streamlit-ingress.yaml
        echo -e "${GREEN}✓ Streamlit deploy edildi${NC}"
        echo ""
        
        echo -e "${YELLOW}Ingress bilgileri:${NC}"
        kubectl get ingress -n mongodb-replica mongodb-streamlit-ingress
        echo ""
        echo -e "${GREEN}Erişim: https://sharemind.tiga.health/dev/streamlit${NC}"
        echo -e "${GREEN}Deployment tamamlandı!${NC}"
    else
        echo -e "${RED}Önce Docker image'ınızı build edip push edin:${NC}"
        echo "  docker build -t your-registry/streamlit-mongo-app:latest ."
        echo "  docker push your-registry/streamlit-mongo-app:latest"
    fi
else
    echo -e "${GREEN}Deployment tamamlandı!${NC}"
fi

echo ""
echo "================================================"
echo "Yararlı Komutlar:"
echo "================================================"
echo "Pod'ları görüntüle:       kubectl get pods -n mongodb-replica"
echo "Replica set durumu:       kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval 'rs.status()'"
echo "PRIMARY node'u bul:       kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval 'db.isMaster()'"
echo "Logları izle:             kubectl logs -f mongodb-0 -n mongodb-replica"
echo "Ingress durumu:           kubectl get ingress -n mongodb-replica"
echo "Streamlit erişim:         https://sharemind.tiga.health/dev/streamlit"
echo "================================================"
