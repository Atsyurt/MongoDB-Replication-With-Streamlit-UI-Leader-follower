#!/bin/bash

set -e

echo "================================================"
echo "MongoDB Replica Set Kubernetes Cleanup"
echo "================================================"
echo ""

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

read -p "Tüm kaynakları silmek istediğinizden emin misiniz? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "İptal edildi."
    exit 1
fi

read -p "PVC'leri (verileri) de silmek istiyor musunuz? (y/n) " -n 1 -r
echo
DELETE_PVC=$REPLY

echo -e "${YELLOW}Kaynaklar siliniyor...${NC}"

# Streamlit'i sil
kubectl delete -f streamlit-deployment.yaml --ignore-not-found=true

# Init job'ı sil
kubectl delete -f mongodb-init-job.yaml --ignore-not-found=true

# StatefulSet'i sil
kubectl delete -f mongodb-statefulset.yaml --ignore-not-found=true

# PVC'leri sil (istenirse)
if [[ $DELETE_PVC =~ ^[Yy]$ ]]
then
    echo -e "${RED}PVC'ler siliniyor (VERİLER SİLİNECEK)...${NC}"
    kubectl delete pvc -n mongodb-replica --all
fi

# Namespace'i sil
kubectl delete namespace mongodb-replica

echo ""
echo -e "${YELLOW}Temizlik tamamlandı!${NC}"
