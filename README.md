# MongoDB Replica Set - Leader/Follower Demo

MongoDB Replica Set (Leader-Follower) yapısını test etmek için Streamlit uygulaması.

## 🎯 Ne Yaptık?

- **4 MongoDB Node** (StatefulSet) - 1 Leader, 3 Follower
- **Streamlit App** - Collection yönetimi, veri ekleme/okuma, failover testleri
- **Kubernetes Deployment** - Azure AKS üzerinde production-ready setup
- **Ingress** - `https://sharemind.tiga.health/dev/streamlit`

**Özellikler:**
✅ Collection oluşturma/seçme
✅ Veri yazma (PRIMARY'ye)
✅ Veri okuma (SECONDARY'lerden)
✅ Read preference testleri
✅ Failover simülasyonu

## 🚀 Hızlı Kurulum

### Docker Compose (Local Test)

```bash
docker-compose up -d --build
```

Erişim: `http://localhost:8501`

### Kubernetes (Production)

**1. Docker Image Build & Push:**
```bash
docker build -t tigard.azurecr.io/streamlit-mongo-app:latest .
docker push tigard.azurecr.io/streamlit-mongo-app:latest
```

**2. Deploy:**
```bash
cd k8s
deploy.bat
```

**3. Erişim:**
```
https://sharemind.tiga.health/dev/streamlit
```

## 📊 Mimari

```
Internet → nginx-sharemind (20.170.87.48)
    ↓
Ingress: /dev/streamlit
    ↓
Streamlit App (ClusterIP)
    ↓
MongoDB StatefulSet (4 pods)
    - mongodb-0 (PRIMARY)
    - mongodb-1, 2, 3 (SECONDARY)
```

## 🧪 Failover Testi

```bash
# Leader'ı durdur
kubectl delete pod mongodb-0 -n mongodb-replica

# Yeni leader seçilir (mongodb-1/2/3)
# Uygulama otomatik devam eder
```

## 🗑️ Temizlik

```bash
cd k8s
undeploy.bat
```

## 📝 Notlar

- **Yazma:** Sadece PRIMARY node
- **Okuma:** SECONDARY_PREFERRED (önce follower'lar)
- **Priority:** mongodb-0 (2), diğerleri (1)
- **Storage:** Her pod 10Gi PVC

## 🔍 Yararlı Komutlar

```bash
# Pod'ları göster
kubectl get pods -n mongodb-replica

# Replica set durumu
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "rs.status()"

# PRIMARY node bul
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "db.isMaster()"

# Streamlit logları
kubectl logs -f deployment/streamlit-app -n mongodb-replica

# Ingress kontrol
kubectl get ingress -n mongodb-replica
```

---
**Hazırlayan:** MongoDB Replica Set Tutorial  
**Erişim:** https://sharemind.tiga.health/dev/streamlit
