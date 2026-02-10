@echo off
setlocal enabledelayedexpansion

echo ================================================
echo MongoDB Replica Set Kubernetes Deployment
echo ================================================
echo.

REM 1. Namespace olustur
echo [93m1. Namespace olusturuluyor...[0m
kubectl apply -f namespace.yaml
if %errorlevel% neq 0 (
    echo [91mHata: Namespace olusturulamadi[0m
    exit /b 1
)
echo [92m✓ Namespace olusturuldu[0m
echo.

REM 2. MongoDB StatefulSet deploy et
echo [93m2. MongoDB StatefulSet deploy ediliyor...[0m
kubectl apply -f mongodb-statefulset.yaml
if %errorlevel% neq 0 (
    echo [91mHata: StatefulSet olusturulamadi[0m
    exit /b 1
)
echo [92m✓ StatefulSet olusturuldu[0m
echo.

REM 3. Pod'larin hazir olmasini bekle
echo [93m3. MongoDB pod'larinin hazir olmasi bekleniyor...[0m
kubectl wait --for=condition=ready pod -l app=mongodb -n mongodb-replica --timeout=300s
if %errorlevel% neq 0 (
    echo [91mHata: Pod'lar hazir degil[0m
    exit /b 1
)
echo [92m✓ Tum pod'lar hazir[0m
echo.

REM 4. Replica set'i baslat
echo [93m4. Replica set baslatiliyor...[0m
kubectl apply -f mongodb-init-job.yaml
if %errorlevel% neq 0 (
    echo [91mHata: Init job baslatılamadi[0m
    exit /b 1
)
echo [92m✓ Init job baslatildi[0m
echo.

REM 5. Job'in tamamlanmasini bekle
echo [93m5. Init job'in tamamlanmasi bekleniyor...[0m
kubectl wait --for=condition=complete job/mongodb-init -n mongodb-replica --timeout=120s
if %errorlevel% neq 0 (
    echo [91mHata: Init job tamamlanamadi[0m
    exit /b 1
)
echo [92m✓ Replica set basariyla baslatildi[0m
echo.

REM 6. Replica set durumunu kontrol et
echo [93m6. Replica set durumu kontrol ediliyor...[0m
kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "rs.status()" --quiet | findstr /C:"name" /C:"stateStr"
echo.

REM 7. Streamlit deploy et (opsiyonel)
set /p deploy_streamlit="Streamlit uygulamasini da deploy etmek istiyor musunuz? (y/n): "
if /i "%deploy_streamlit%"=="y" (
    echo [93m7. Streamlit uygulamasi deploy ediliyor...[0m
    
    set /p image_ready="Docker image'inizi push ettiniz mi? (y/n): "
    if /i "!image_ready!"=="y" (
        kubectl apply -f streamlit-deployment.yaml
        kubectl apply -f streamlit-ingress.yaml
        echo [92m✓ Streamlit deploy edildi[0m
        echo.
        
        echo [93mIngress bilgileri:[0m
        kubectl get ingress -n mongodb-replica mongodb-streamlit-ingress
        echo.
        echo [92mErisim: https://sharemind.tiga.health/dev/streamlit[0m
        echo [92mDeployment tamamlandi![0m
    ) else (
        echo [91mOnce Docker image'inizi build edip push edin:[0m
        echo   docker build -t your-registry/streamlit-mongo-app:latest .
        echo   docker push your-registry/streamlit-mongo-app:latest
    )
) else (
    echo [92mDeployment tamamlandi![0m
)

echo.
echo ================================================
echo Yararli Komutlar:
echo ================================================
echo Pod'lari goruntule:       kubectl get pods -n mongodb-replica
echo Replica set durumu:       kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "rs.status()"
echo PRIMARY node'u bul:       kubectl exec -it mongodb-0 -n mongodb-replica -- mongosh --eval "db.isMaster()"
echo Loglari izle:             kubectl logs -f mongodb-0 -n mongodb-replica
echo Ingress durumu:           kubectl get ingress -n mongodb-replica
echo Streamlit erisim:         https://sharemind.tiga.health/dev/streamlit
echo ================================================

pause
