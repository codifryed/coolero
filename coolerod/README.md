# CooleroD

is a system and session daemon, which communicates with and collects data from - various connected devices. It then make
this data and functionallity available to the Coolero frontend.

- It is written in rust with integration with python to enable use of the liquidctl python api independant of
  system installed packages.
- It can be used as a systemd service with a systemd socket which can be started at boot. This requires that the correct
  Systemd Unit files are setup and installed correctly.
- It can also be used as a one-off session daemon, which is more suitable for portable installation methods like
  AppImage. This requires superuser access at run time.

This makes use of the pyoxidizer project to embed a python interpreter and needed libraries into the executable itself.
This has the advantage of a full functioning service that is independent of the Coolero frontend.

Also in use is gRPC, which is not only fast and efficient, but allows us to use the same protocol description and write
the server in Rust, and the client (Coolero) in Python.

Rust is the choosen language for the server due to the fact that we wanted the best performance with lowest resource
cost to have always running in the background, and its natural integration with system libraries and functions.
