from setuptools import find_packages, setup

package_name = 'drone_basics_py'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    package_data={'': ['py.typed']},
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='joao-barros',
    maintainer_email='joao-barros@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'setpoint_pub = drone_basics_py.setpoint_pub:main',
            'radio_teleop = drone_basics_py.radio_teleop:main',
        ],
    },
)
