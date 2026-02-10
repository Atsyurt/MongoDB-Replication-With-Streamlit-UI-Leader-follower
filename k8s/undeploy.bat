@echo off
setlocal

echo ================================================
echo MongoDB Replica Set Kubernetes Cleanup
echo ================================================
echo.

set /p confirm="Tum kaynaklari silmek istediginizden emin misiniz? (y/n): "
if /i not "%confirm%"=="y" (
    echo Iptal edildi.
    exit /b 0
)

set /p delete_pvc="PVC'leri (verileri) de silmek istiyor musunuz? (y/n): "

echo [93mKaynaklar siliniyor...[0m

REM Streamlit'i sil
kubectl delete -f streamlit-ingress.yaml --ignore-not-found=true
kubectl delete -f streamlit-deployment.yaml --ignore-not-found=true

REM Init job'i sil
kubectl delete -f mongodb-init-job.yaml --ignore-not-found=true

REM StatefulSet'i sil
kubectl delete -f mongodb-statefulset.yaml --ignore-not-found=true

REM PVC'leri sil (istenirse)
if /i "%delete_pvc%"=="y" (
    echo [91mPVC'ler siliniyor (VERILER SILINECEK)...[0m
    kubectl delete pvc -n mongodb-replica --all
)

REM Namespace'i sil
kubectl delete namespace mongodb-replica

echo.
echo [93mTemizlik tamamlandi![0m

pause
