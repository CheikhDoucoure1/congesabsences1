@echo off
echo ==========================================
echo  PETROSEN - Gestion Conges et Absences
echo ==========================================
echo.
echo Demarrage du serveur sur http://127.0.0.1:8001
echo.
echo Comptes de connexion:
echo   Admin    : admin@petrosen.sn / admin123
echo   DRH      : drh@petrosen.sn / password
echo   Manager  : manager@petrosen.sn / password
echo   Employe  : employe@petrosen.sn / password
echo.
echo Appuyez sur Ctrl+C pour arreter le serveur
echo ==========================================
py manage.py runserver 8001
pause
