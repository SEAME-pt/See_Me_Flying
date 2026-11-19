from setuptools import find_packages, setup

package_name = 'drone_safety'

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
    description='safety_manager: picks which command source reaches fc_bridge.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'safety_manager = drone_safety.safety_manager:main',
        ],
    },
)
