echo ________ Environment __________
pip list
env
pwd
ls -alh
echo ______ End Of Environment _____
sns_va &
VA_PID=$(jobs -p)
echo PID of VA is $VA_PID
python virtaccl/examples/Corrector.py
RESULT=$?
jobs -l
kill -9 $VA_PID 2>&1
sleep 1
echo Test result is $RESULT
exit $RESULT
