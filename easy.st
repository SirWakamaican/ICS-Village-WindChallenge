PROGRAM easy
  VAR
    ESTOP AT %QX1.0 : BOOL;
    turbine AT %QX50 : BOOL;
  END_VAR

  turbine := ESTOP;
END_PROGRAM

PROGRAM med
  VAR
    ESTOP AT %QX1.0 : BOOL;
    turbine AT %QX50 : BOOL;
  END_VAR
  VAR
    CTU0 : CTU;
    count_value : INT := 0;
    cv_target : INT := 1;
    reset : BOOL;
    R_TRIG1 : R_TRIG;
  END_VAR

  R_TRIG1(CLK := ESTOP);
  CTU0(CU := R_TRIG1.Q, R := reset, PV := cv_target);
  count_value := CTU0.CV;
  turbine := CTU0.Q;
END_PROGRAM


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms,PRIORITY := 0);
    PROGRAM instance0 WITH task0 : easy;
  END_RESOURCE
END_CONFIGURATION
