import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/joao-barros/Documents/ros2_ws/install/drone_basics_py'
