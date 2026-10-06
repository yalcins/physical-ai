import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

WORLD = os.environ["CAPTURE_WORLD"]   # make_world.py ciktisi


def generate_launch_description():
    pkg = get_package_share_directory('arena_sim')
    urdf = open(os.path.join(pkg, 'urdf', 'pai_bot.urdf')).read()
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': f'-s -r --headless-rendering {WORLD}'}.items())
    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher',
               parameters=[{'robot_description': urdf, 'use_sim_time': True}])
    spawn = Node(package='ros_gz_sim', executable='create',
                 arguments=['-name', 'pai_bot', '-topic', 'robot_description',
                            '-x', '-0.6', '-y', '-0.6', '-z', '0.01', '-Y', '0.785'])
    bridge = Node(package='ros_gz_bridge', executable='parameter_bridge',
                  parameters=[{'config_file': os.path.join(pkg, 'config', 'bridge.yaml'), 'use_sim_time': True}])
    img = Node(package='ros_gz_bridge', executable='parameter_bridge',
               arguments=['/overhead/image@sensor_msgs/msg/Image[gz.msgs.Image'],
               parameters=[{'use_sim_time': True}])
    tof = Node(package='arena_sim', executable='tof_range_node', parameters=[{'use_sim_time': True}])
    moving = Node(package='arena_sim', executable='moving_obstacles_node', parameters=[{'use_sim_time': True}])
    nodes = [gazebo, rsp, spawn, bridge, img, tof]
    if not os.environ.get('CAPTURE_NO_MOVING'):        # testlerde hareketli engeller kapatilabilir
        nodes.append(moving)
    return LaunchDescription(nodes)
