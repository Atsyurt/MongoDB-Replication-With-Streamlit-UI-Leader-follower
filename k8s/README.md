# Kubernetes Deployment - MongoDB Replica Set

Bu dizinde MongoDB Replica Set'i Kubernetes cluster'ına deploy etmek için gerekli manifest dosyaları bulunur.

## 📋 Dosyalar

- `namespace.yaml` - mongodb-replica namespace'i
- `mongodb-statefulset.yaml` - 4 MongoDB pod'u (StatefulSet)
- `mongodb-init-job.yaml` - Replica set'i başlatan Job
- `streamlit-deployment.yaml` - Streamlit uygulaması

## 🚀 Deployment Adımları

### 1. Docker Image Oluştur ve Push Et

```bash
# Streamlit uygulaması için image build et
docker build -t your-registry/streamlit-mongo-app:latest .

# Registry'ye push et (Docker Hub, ECR, GCR, vb.)
docker push your-registry/streamlit-mongo-app:latest
```

**Not:** `streamlit-deployment.yaml` dosyasındaki `image` alanını kendi registry URL'nizle güncelleyin.

### 2. Namespace Oluştur

```bash
kubectl apply -f k8s/namespace.yaml
```

### 3. MongoDB StatefulSet Deploy Et

```bash
kubectl apply -f k8s/mongodb-statefulset.yaml
```

Bu komut:
- Headless service oluşturur
- 4 MongoDB pod'u başlatır (mongodb-0, mongodb-1, mongodb-2, mongodb-3)
- Her pod için 10Gi PersistentVolume oluşturur

Pod'ların çalıştığını kontrol edin:
```bash
kubectl get pods -n mongodb-replica -w
```

Tüm pod'lar `Running` durumunda olana kadar bekleyin (yaklaşık 2-3 dakika).

### 4. Replica Set'i Başlat

```bash
kubectl apply -f k8s/mongodb-init-job.yaml
```

Job'ın tamamlandığını kontrol edin:
```bash
kubectl get jobs -n mongodb-replica
kubectl logs -n mongodb-replica job/mongodb-init
```

Başarılı log çıktısı:
```
Replica set başlatılıyor...
Replica set başarıyla başlatıldı!
İşlem tamamlandı!
```

### 5. Replica Set Durumunu Kontrol Et

```bash
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "rs.status()"
```

PRIMARY ve SECONDARY node'ları göreceksiniz.

### 6. Streamlit Uygulamasını Deploy Et

```bash
kubectl apply -f k8s/streamlit-deployment.yaml
```

Service'in external IP'sini alın:
```bash
kubectl get svc -n mongodb-replica streamlit-service
```

**LoadBalancer:** External IP gelene kadar bekleyin, ardından tarayıcıdan erişin.
**NodePort:** Node IP + NodePort ile erişin (örn: `http://192.168.1.100:30080`)

## 🔍 Monitoring ve Debugging

### Pod Durumlarını Görüntüle
```bash
kubectl get pods -n mongodb-replica
kubectl describe pod mongodb-0 -n mongodb-replica
```

### Logları İzle
```bash
# MongoDB pod logları
kubectl logs -f mongodb-0 -n mongodb-replica

# Streamlit pod logları
kubectl logs -f deployment/streamlit-app -n mongodb-replica
```

### Pod'a Bağlan
```bash
# MongoDB'ye shell ile bağlan
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh

# Streamlit pod'a bağlan
kubectl exec -it deployment/streamlit-app -n mongodb-replica -- /bin/bash
```

### Replica Set Durumunu Kontrol Et
```bash
# Replica set durumu
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "rs.status()"

# PRIMARY node'u bul
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "db.isMaster()"

# Her node'u kontrol et
for i in {0..3}; do
  echo "=== mongodb-$i ==="
  kubectl exec -it mongodb-$i -n mongodb-replica -- mongosh --eval "db.isMaster().ismaster"
done
```

## 🧪 Test Senaryoları

### 1. Pod Restart Testi
```bash
# Bir pod'u sil (otomatik yeniden oluşturulur)
kubectl delete pod mongodb-1 -n mongodb-replica

# Durumu izle
kubectl get pods -n mongodb-replica -w
```

### 2. Leader Failover Testi
```bash
# PRIMARY pod'u bul
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "rs.status()" | grep PRIMARY

# PRIMARY pod'u sil
kubectl delete pod mongodb-0 -n mongodb-replica

# Yeni PRIMARY seçilmesini izle
watch kubectl exec -it mongodb-1 -n mongodb-replica -- mongosh --eval "rs.status().members" 2>/dev/null
```

### 3. Scale Test (Opsiyonel)
```bash
# Replica sayısını artır
kubectl scale statefulset mongodb -n mongodb-replica --replicas=5

# Yeni pod'u replica set'e ekle
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval '
  rs.add({
    _id: 4,
    host: "mongodb-4.mongodb-service.mongodb-replica.svc.cluster.local:27017",
    priority: 1
  })
'
```

## 📊 Mimari

```
┌─────────────────────────────────────────────┐
│         Kubernetes Cluster                  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   Namespace: mongodb-replica         │  │
│  │                                      │  │
│  │  ┌──────────────────────────────┐   │  │
│  │  │  StatefulSet: mongodb        │   │  │
│  │  │                              │   │  │
│  │  │  ├─ mongodb-0 (PRIMARY)      │   │  │
│  │  │  │  └─ PVC: 10Gi             │   │  │
│  │  │  │                           │   │  │
│  │  │  ├─ mongodb-1 (SECONDARY)    │   │  │
│  │  │  │  └─ PVC: 10Gi             │   │  │
│  │  │  │                           │   │  │
│  │  │  ├─ mongodb-2 (SECONDARY)    │   │  │
│  │  │  │  └─ PVC: 10Gi             │   │  │
│  │  │  │                           │   │  │
│  │  │  └─ mongodb-3 (SECONDARY)    │   │  │
│  │  │     └─ PVC: 10Gi             │   │  │
│  │  └──────────────────────────────┘   │  │
│  │                                      │  │
│  │  ┌──────────────────────────────┐   │  │
│  │  │  Deployment: streamlit-app   │   │  │
│  │  │  └─ Replicas: 1              │   │  │
│  │  └──────────────────────────────┘   │  │
│  │                                      │  │
│  │  ┌──────────────────────────────┐   │  │
│  │  │  Service: streamlit-service  │   │  │
│  │  │  Type: LoadBalancer          │   │  │
│  │  │  Port: 80 → 8501             │   │  │
│  │  └──────────────────────────────┘   │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## 🛠️ Storage

StatefulSet her pod için otomatik olarak PersistentVolumeClaim oluşturur:
- `mongodb-data-mongodb-0` → 10Gi
- `mongodb-data-mongodb-1` → 10Gi
- `mongodb-data-mongodb-2` → 10Gi
- `mongodb-data-mongodb-3` → 10Gi

### Storage Class Değiştirme
Eğer farklı storage class kullanmak isterseniz, `mongodb-statefulset.yaml` içinde:

```yaml
volumeClaimTemplates:
- metadata:
    name: mongodb-data
  spec:
    storageClassName: fast-ssd  # Kendi storage class'ınız
    accessModes: [ "ReadWriteOnce" ]
    resources:
      requests:
        storage: 10Gi
```

## 🔐 Production İyileştirmeleri

### 1. Authentication Ekle
```bash
# Secret oluştur
kubectl create secret generic mongodb-secret \
  --from-literal=username=admin \
  --from-literal=password=secure-password \
  -n mongodb-replica
```

StatefulSet'e environment variable ekle:
```yaml
env:
- name: MONGO_INITDB_ROOT_USERNAME
  valueFrom:
    secretKeyRef:
      name: mongodb-secret
      key: username
- name: MONGO_INITDB_ROOT_PASSWORD
  valueFrom:
    secretKeyRef:
      name: mongodb-secret
      key: password
```

### 2. Resource Limits Ayarla
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### 3. Anti-Affinity Ekle
Pod'ları farklı node'lara dağıt:
```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchExpressions:
        - key: app
          operator: In
          values:
          - mongodb
      topologyKey: kubernetes.io/hostname
```

### 4. Monitoring Ekle
```bash
# Prometheus ServiceMonitor
kubectl apply -f k8s/prometheus-servicemonitor.yaml
```

## 🗑️ Temizlik

### Tüm kaynakları sil
```bash
kubectl delete namespace mongodb-replica
```

### Sadece uygulamayı sil (data kalsın)
```bash
kubectl delete -f k8s/streamlit-deployment.yaml
kubectl delete -f k8s/mongodb-init-job.yaml
```

### PVC'leri de sil
```bash
kubectl delete pvc -n mongodb-replica --all
```

## 📝 Notlar

- **StatefulSet** kullanıyoruz çünkü MongoDB gibi stateful uygulamalar için idealdir
- Her pod **stable network identity** alır (mongodb-0, mongodb-1, etc.)
- **Headless Service** sayesinde her pod DNS adresine sahip
- Pod restart olsa bile aynı PVC'ye bağlanır (data kaybolmaz)
- **Priority 2** ile mongodb-0 öncelikli leader olur

## 🆘 Sorun Giderme

### Pod başlamıyor
```bash
kubectl describe pod mongodb-0 -n mongodb-replica
kubectl logs mongodb-0 -n mongodb-replica
```

### PVC oluşturulmuyor
```bash
kubectl get pvc -n mongodb-replica
kubectl describe pvc mongodb-data-mongodb-0 -n mongodb-replica

# Storage class kontrol et
kubectl get storageclass
```

### Replica set başlatılamıyor
```bash
# Job loglarını kontrol et
kubectl logs job/mongodb-init -n mongodb-replica

# Manuel başlatma
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh
rs.initiate({...})
```

### Streamlit bağlanamıyor
```bash
# ConfigMap'i kontrol et
kubectl get configmap streamlit-config -n mongodb-replica -o yaml

# DNS çözümleme testi
kubectl exec -it deployment/streamlit-app -n mongodb-replica -- nslookup mongodb-0.mongodb-service.mongodb-replica.svc.cluster.local
```
