#!/usr/bin/env  python
# coding:utf-8
import numpy as np
import math
import matplotlib.pyplot as plt
import functions
from statistics import variance

class RobotKick:
    def __init__(self, ball_params, ctrld_robot, pid, cmd, status, command_pub):
        self.kick_power_x = 10
        self.kick_power_z = 0

        self.ball_params = ball_params
        self.ctrld_robot = ctrld_robot
        self.pid = pid
        self.status = status
        self.cmd = cmd
        self.command_pub = command_pub
        self.dispersion1 = [10] * 1
        self.dispersion2 = [10] * 1
        self.rot_dispersion = [10] * 1

        self.access_threshold1 = 0.1
        self.access_threshold2 = 0.5
        self.feint_threshold1 = 0.15
        self.feint_threshold2 = 1.0 
        self.rot_access_threshold = 0.015
        self.pass_stage = 0

        self.access_threshold = 5
        #self.const = 1.5
        self.const = 2

        self.ball_frame = 60 #ボールの軌道直線フィッティングと速度の計算フレーム
        self.ball_pos_x_array = np.array([0.0]*self.ball_frame)
        self.ball_pos_y_array = np.array([0.0]*self.ball_frame)
        self.reach_flag = False
        self.ball_pos_count = 0
        self.ball_speed = 0
        self.ball_accel = 0
        self.ball_reach_time = 0
        self.ball_speed_calc_count = 0

        self.plot_x = np.arange(-5.0,5.0, 0.01)
        self.plot_y = np.arange(-5.0,5.0, 0.01)
        self.fig, self.ax = plt.subplots(1, 1)
        # 初期化的に一度plotしなければならない
        # そのときplotしたオブジェクトを受け取る受け取る必要がある．
        # listが返ってくるので，注意
        self.lines1, = self.ax.plot(self.ball_pos_x_array, self.ball_pos_y_array)
        self.lines2, = self.ax.plot(self.plot_x, self.plot_y)
        self.lines3, = self.ax.plot(self.plot_x, self.plot_y)
        self.lines4, = self.ax.plot(self.plot_x, self.plot_y)
        self.ax.set_xlim(-5, 5)
        self.ax.set_ylim(-5, 5)

    def kick_x(self):
        area = 0.5
        if math.sqrt((self.ball_params.get_current_position()[0] - self.ctrld_robot.get_current_position()[0])**2 + (self.ball_params.get_current_position()[1] - self.ctrld_robot.get_current_position()[1])**2) > self.ctrld_robot.size_r + area:
            self.cmd.vel_surge = 0
            self.cmd.vel_sway = 0
            self.cmd.omega = 0
            self.cmd.kick_speed_x = 0
            self.command_pub.publish(self.cmd)
            self.status.robot_status = "None"
            self.pass_stage = 0
            self.dispersion1 = [10] * 1
            self.dispersion2 = [10] * 1
            return

        self.cmd.kick_speed_x = self.kick_power_x
        self.pid.pid_linear(self.ball_params.get_current_position()[0], self.ball_params.get_current_position()[1], self.pose_theta)
        #self.cmd.vel_surge = 3
        self.command_pub.publish(self.cmd)

    def pass_ball(self, target_x, target_y):
        distance = math.sqrt((target_x - self.ball_params.get_current_position()[0])**2 + (target_y - self.ball_params.get_current_position()[1])**2)
        if distance != 0:
            #print self.pass_stage
            if self.pass_stage == 0:
                pose_x = (- 0.3 * target_x + (0.3 + distance) * self.ball_params.get_current_position()[0]) / distance
                pose_y = (- 0.3 * target_y + (0.3 + distance) * self.ball_params.get_current_position()[1]) / distance
                pose_theta = math.atan2( (target_y - self.ctrld_robot.get_current_position()[1]) , (target_x - self.ctrld_robot.get_current_position()[0]) )

                a, b, c = functions.line_parameters(self.ball_params.get_current_position()[0], self.ball_params.get_current_position()[1], target_x, target_y)

                self.dispersion1.append(
                        functions.distance_of_a_point_and_a_straight_line(self.ctrld_robot.get_current_position()[0], self.ctrld_robot.get_current_position()[1], a, b, c))
                        #(pose_x - self.ctrld_robot.get_current_position()[0])**2 \
                        #+ (pose_y - self.ctrld_robot.get_current_position()[1])**2)
                del self.dispersion1[0]

                self.dispersion2.append(
                        (pose_x - self.ctrld_robot.get_current_position()[0])**2 \
                        + (pose_y - self.ctrld_robot.get_current_position()[1])**2)
                del self.dispersion2[0]

                dispersion_average1 = sum(self.dispersion1)/len(self.dispersion1)
                dispersion_average2 = sum(self.dispersion2)/len(self.dispersion2)

                if dispersion_average1 > self.feint_threshold1 or dispersion_average2 > self.feint_threshold2:
                    pose_theta += np.pi/3.

                self.rot_dispersion.append((pose_theta - self.ctrld_robot.get_current_orientation())**2)
                del self.rot_dispersion[0]
                rot_dispersion_average = sum(self.rot_dispersion)/len(self.rot_dispersion)

                # print("{} {}".format(dispersion_average, rot_dispersion_average))

                if dispersion_average1 < self.access_threshold1 and dispersion_average2 < self.access_threshold2 and rot_dispersion_average < self.rot_access_threshold:
                    self.kick_power_x = math.sqrt(distance) * self.const
                    self.pose_theta = pose_theta
                    self.status.robot_status = "kick"
                    #self.pass_stage = 1
            """
            if self.pass_stage == 1:
                self.kick_power_x = math.sqrt(distance) * self.const
                self.pose_theta = pose_theta
                self.status.robot_status = "kick"
            """
            
            self.pid.pid_linear(pose_x, pose_y, pose_theta)

    def kick_z(self):
        pass

    def reg1dim(self, x, y, n):
        x = np.clip(x,-5,5)
        y = np.clip(y,-5,5)
        a = ((np.dot(x, y)- y.sum() * x.sum()/n) / ((x ** 2).sum() - x.sum()**2 / n))
        b = (y.sum() - a * x.sum())/n
        a = np.clip(a,-1.0e+308,1.0e+308)
        b = np.clip(b,-1.0e+308,1.0e+308)
        return a, b

    def receive_ball(self, target_x, target_y):

        """ self.reach_flag = True
        #目標点まで移動
        if self.reach_flag == False:
            pose_theta = math.atan2( (self.ball_params.get_current_position()[1] - target_y) , (self.ball_params.get_current_position()[0] - target_x) )
            self.pid.pid_linear(target_x, target_y, pose_theta)
            distance = math.sqrt((target_x - self.ctrld_robot.get_current_position()[0])**2 + (target_y - self.ctrld_robot.get_current_position()[1])**2)
            if distance < 0.1:
                self.reach_flag = False
                #print("reach")
            #else:
                #print(distance) """

        #直近60フレームの座標を取得
        """ if self.ball_pos_count < self.ball_frame:
            self.ball_pos_x_array[self.ball_pos_count] = self.ball_params.get_current_position()[0]
            self.ball_pos_y_array[self.ball_pos_count] = self.ball_params.get_current_position()[1]
            self.ball_pos_count+=1
        else:
            self.ball_pos_x_array = np.roll(self.ball_pos_x_array,-1)
            self.ball_pos_y_array = np.roll(self.ball_pos_y_array,-1)
            self.ball_pos_x_array[self.ball_pos_count-1] = self.ball_params.get_current_position()[0]
            self.ball_pos_y_array[self.ball_pos_count-1] = self.ball_params.get_current_position()[1]
            #x,y座標の分散を計算
            x_variance = variance(self.ball_pos_x_array)
            y_variance = variance(self.ball_pos_y_array)
            #print(x_variance,y_variance)
            #分散が1より大きかったらカウントリセット
            if x_variance > 1 or y_variance > 1:
                self.ball_pos_count = 0
                for i in range(0,self.ball_frame):
                    self.ball_pos_x_array[i] = 0
                    self.ball_pos_y_array[i] = 0 """

        if self.ball_pos_count == 0:
            #a, b = self.reg1dim(self.ball_pos_x_array, self.ball_pos_y_array, self.ball_pos_count)
            # 本来のパス目標地点と実際の直線Lとの距離計算
            d = (abs(self.ball_params.get_line_a()*target_x - target_y + self.ball_params.get_line_b()))/((self.ball_params.get_line_a()**2 + 1)**(1/2)) # ヘッセの公式で距離計算
            # 交点H(hx, hy) の座標計算
            hx = (self.ball_params.get_line_a()*(target_y - self.ball_params.get_line_b()) + target_x)/(self.ball_params.get_line_a()**2 + 1)
            hy = self.ball_params.get_line_a()*(self.ball_params.get_line_a()*(target_y - self.ball_params.get_line_b()) + target_x)/(self.ball_params.get_line_a()**2 + 1) + self.ball_params.get_line_b()

            """ #機体の速度・加速度から間に合うかどうか判断
            #ボールとパス目標点との距離を計算
            ball_distance_target = math.sqrt((target_x - self.ball_params.get_current_position()[0])**2 + (target_y - self.ball_params.get_current_position()[1])**2)
            #ボールのスピードを計算 計算フレーム:可変
            ball_speed_calc_frame = 10
            if (self.ball_pos_count%ball_speed_calc_frame) == 0 and (self.ball_pos_count-1) > 0 and self.ball_speed_calc_count >= ball_speed_calc_frame:
                old_ball_speed = self.ball_speed
                self.ball_speed = math.sqrt((self.ball_pos_x_array[self.ball_pos_count-1] - self.ball_pos_x_array[self.ball_pos_count-ball_speed_calc_frame-1])**2 + \
                    (self.ball_pos_y_array[self.ball_pos_count-1] - self.ball_pos_y_array[self.ball_pos_count-ball_speed_calc_frame-1])**2) / ((1./self.ball_frame)*ball_speed_calc_frame)
                self.ball_accel = (old_ball_speed - self.ball_speed) / ((1./self.ball_frame)*ball_speed_calc_frame)
                self.ball_speed_calc_count = 0
            else:
                self.ball_speed_calc_count+=1
            #ボールが何秒後に交点につくかを計算
            if self.ball_accel < 0:
                self.ball_reach_time = self.ball_speed / abs(self.ball_accel)
            #print('{:>12.5f},{:>12.5f},{:>12.5f},{:>12.5f}'.format(self.ball_pos_count,self.ball_speed,self.ball_accel,self.ball_reach_time))
            #print('{:>12.5f},{:>12.5f}'.format(self.ball_params.get_current_position()[0],self.ball_params.get_current_position()[1])) """

            #距離だけで諦めるかどうか判断
            pose_theta = math.atan2( (self.ball_params.get_current_position()[1] - target_y) , (self.ball_params.get_current_position()[0] - target_x) )
            self.pid.pid_linear(self.ball_params.get_future_position()[0], self.ball_params.get_future_position()[1], pose_theta)
            """ if d < 2:
                pose_theta = math.atan2( (self.ball_params.get_current_position()[1] - hy) , (self.ball_params.get_current_position()[0] - hx) )
                self.pid.pid_linear(hx, hy, pose_theta)
            else:
                pose_theta = math.atan2( (self.ball_params.get_current_position()[1] - target_y) , (self.ball_params.get_current_position()[0] - target_x) )
                self.pid.pid_linear(target_x, target_y, pose_theta) """

            # 垂線テキスト座標
            dx_center = (target_x + hx) / 2
            dy_center = (target_y + hy) / 2
            # plt.axis('scaled')
            #plt.plot([target_x, hx],[target_y, hy], color='green', linestyle='--', zorder=0)

            self.plot_y = self.ball_params.get_line_a() * self.plot_x + self.ball_params.get_line_b()
            self.lines1.set_data(self.ball_pos_x_array, self.ball_pos_y_array)
            self.lines2.set_data(self.plot_x, self.plot_y)
            self.lines3.set_data([target_x, hx], [target_y, hy])
            #self.lines3.set_data([self.ball_params.get_future_position()[0], hx], [self.ball_params.get_future_position()[1], hy])
            self.lines4.set_data([self.ball_params.get_future_position()[0], target_x], [self.ball_params.get_future_position()[1], target_y])
            plt.pause(.01)

