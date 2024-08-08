PROGRAM program0
  VAR
    VoltageChk AT %IX0.0 : BOOL := 0;
    Sensor AT %IX0.1 : BOOL;
    Turbine AT %QX10 : BOOL := 0;
    Trip AT %QX0.0 : BOOL := 0;
    Fault AT %QX0.1 : BOOL := 0;
    FaultLight AT %QX0.4 : BOOL := 0;
    Reset AT %QX0.6 : BOOL := 0;
    Teleruptor AT %QW15 : INT := 0;
  END_VAR
  VAR
    Ttime : TIME;
    CTU0 : CTU;
    TOF0 : TOF;
    R_TRIG1 : R_TRIG;
    _TMP_EQ49_OUT : BOOL;
  END_VAR

  Trip := Fault;
  Turbine := NOT(Trip) AND VoltageChk;
  VoltageChk := Sensor;
  R_TRIG1(CLK := Fault);
  CTU0(CU := R_TRIG1.Q, R := Reset, PV := 3);
  Trip := CTU0.Q;
  TOF0(IN := Fault, PT := T# 15000ms);
  FaultLight := TOF0.Q;
  Teleruptor := CTU0.CV;
  _TMP_EQ49_OUT := EQ(Ttime, T# 15000ms);
  Reset := _TMP_EQ49_OUT;
  Ttime := TOF0.ET;
END_PROGRAM


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms,PRIORITY := 0);
    PROGRAM instance0 WITH task0 : program0;
  END_RESOURCE
END_CONFIGURATION
