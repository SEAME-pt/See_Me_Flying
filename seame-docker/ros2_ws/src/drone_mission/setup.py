from setuptools import find_packages, setup

package_name = 'drone_mission'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='João Barros',
    maintainer_email='joao.barros@seame.pt',
    description='mission: Takeoff, Goto and Land action servers on the rangefinder.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'mission = drone_mission.mission:main',
            'demo_flight = drone_mission.demo_flight:main',
        ],
    },
)
