import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('arena_sim')
    world = os.path.join(pkg, 'worlds', 'arena.sdf')
    urdf = os.path.join(pkg, 'urdf', 'pai_bot.urdf')
    bridge_cfg = os.path.join(pkg, 'config', 'bridge.yaml')

    with open(urdf, 'r') as f:
        robot_description = f.read()

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': f'-r {world}'}.items(),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
        output='screen',
    )

    # Robotu arenanin sol alt kosesine, merkeze bakacak sekilde koy
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'pai_bot', '-topic', 'robot_description',
                   '-x', '-0.6', '-y', '-0.6', '-z', '0.01', '-Y', '0.785'],
        output='screen',
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_cfg, 'use_sim_time': True}],
        output='screen',
    )

    tof = Node(
        package='arena_sim',
        executable='tof_range_node',
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    # Hareketli engeller (moving_1, moving_2) duvarlardan seker
    moving = Node(
        package='arena_sim',
        executable='moving_obstacles_node',
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription([gazebo, robot_state_publisher, spawn, bridge, tof, moving])
