cmake_minimum_required(VERSION 2.8.3)
project(launch_manager)

find_package(catkin REQUIRED COMPONENTS
  consai_msgs
  rospy
)

catkin_package()

include_directories(
  ${catkin_INCLUDE_DIRS}
)
