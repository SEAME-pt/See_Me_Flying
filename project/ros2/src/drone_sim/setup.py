from setuptools import find_packages, setup

package_name = 'drone_sim'

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
    maintainer='David Roque',
    maintainer_email='david.roque@seame.pt',
    description='Simulation-only nodes: optical flow model, estimator and flow check.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'flow_model = drone_sim.flow_model:main',
            'flow_check = drone_sim.flow_check:main',
            'odom_check = drone_sim.odom_check:main',
            'estimator = drone_sim.estimator_node:main',
            'depth_view = drone_sim.depth_view:main',
            'sweep_view = drone_sim.sweep_view:main',
            'path_viz = drone_sim.path_viz_node:main',
        ],
    },
)
