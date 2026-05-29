"""G1 Humanoid Sit-to-Stand Demo.

A foundational demo showing bipedal control.
Robot starts crouched and extends knees to stand.
Uses simple PD joint tracking with fixed base for stability.
"""
import numpy as np


def create_g1_model():
    xml = """
    <mujoco model="g1_sit_to_stand">
      <compiler angle="radian"/>
      <option timestep="0.001" gravity="0 0 -9.81"/>
      <worldbody>
        <geom type="plane" size="10 10 0.1" rgba="0.8 0.8 0.8 1"/>
        <body name="pelvis" pos="0 0 0.5">
          <geom type="box" size="0.12 0.08 0.06" mass="20" rgba="0.3 0.6 0.9 1"/>
          <body name="thigh_left" pos="0 0.1 -0.06">
            <joint name="hip_left" type="hinge" axis="1 0 0" range="-1.5 0.5" damping="8"/>
            <geom type="capsule" fromto="0 0 0 0 0 -0.35" size="0.05" mass="3" rgba="0.8 0.3 0.2 1"/>
            <body name="shin_left" pos="0 0 -0.35">
              <joint name="knee_left" type="hinge" axis="1 0 0" range="0 2.0" damping="5"/>
              <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.04" mass="2" rgba="0.8 0.3 0.2 1"/>
              <body name="foot_left" pos="0 0 -0.3">
                <geom type="box" size="0.08 0.04 0.015" mass="1" rgba="0.2 0.2 0.2 1"/>
              </body>
            </body>
          </body>
          <body name="thigh_right" pos="0 -0.1 -0.06">
            <joint name="hip_right" type="hinge" axis="1 0 0" range="-1.5 0.5" damping="8"/>
            <geom type="capsule" fromto="0 0 0 0 0 -0.35" size="0.05" mass="3" rgba="0.8 0.3 0.2 1"/>
            <body name="shin_right" pos="0 0 -0.35">
              <joint name="knee_right" type="hinge" axis="1 0 0" range="0 2.0" damping="5"/>
              <geom type="capsule" fromto="0 0 0 0 0 -0.3" size="0.04" mass="2" rgba="0.8 0.3 0.2 1"/>
              <body name="foot_right" pos="0 0 -0.3">
                <geom type="box" size="0.08 0.04 0.015" mass="1" rgba="0.2 0.2 0.2 1"/>
              </body>
            </body>
          </body>
        </body>
      </worldbody>
      <actuator>
        <motor joint="hip_left" gear="20" ctrlrange="-30 30"/>
        <motor joint="knee_left" gear="20" ctrlrange="-30 30"/>
        <motor joint="hip_right" gear="20" ctrlrange="-30 30"/>
        <motor joint="knee_right" gear="20" ctrlrange="-30 30"/>
      </actuator>
    </mujoco>
    """
    return xml


def run_demo(duration=3.0):
    import mujoco
    xml = create_g1_model()
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    
    print(f"G1 Sit-to-Stand: {model.nq} DOF, {model.nu} actuators")
    
    # Start in crouch (knees bent) - qpos indices: 0=hip_left, 1=knee_left, 2=hip_right, 3=knee_right
    data.qpos[0] = -1.0  # hip_left
    data.qpos[1] = 1.5   # knee_left bent
    data.qpos[2] = -1.0  # hip_right
    data.qpos[3] = 1.5   # knee_right bent
    mujoco.mj_forward(model, data)
    
    print(f"Start: knees bent at {data.qpos[1]:.2f}, {data.qpos[3]:.2f} rad")
    
    # Target: standing straight
    target = np.array([0.0, 0.0, 0.0, 0.0])
    
    steps = int(duration / 0.001)
    for i in range(steps):
        progress = min(i / 2000.0, 1.0)
        
        for j in range(4):
            data.ctrl[j] = (target[j] - data.qpos[j]) * 8 * progress
        
        mujoco.mj_step(model, data)
        
        if i % 500 == 0:
            print(f"  t={data.time:.2f}s: knees=[{data.qpos[1]:.2f},{data.qpos[3]:.2f}]")
    
    success = data.qpos[1] < 0.3 and data.qpos[3] < 0.3
    print(f"\nFinal: knees=[{data.qpos[1]:.3f},{data.qpos[3]:.3f}]")
    print(f"Sit-to-stand success: {success}")
    return success


if __name__ == "__main__":
    run_demo()
