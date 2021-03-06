Setting up wxPtyhon with virtualenv is quite painful:
- carry on with business as usual
  - virtualenv -p python3 --no-site-packages --distribution <name>
- you need to use a framework version of python which venv don't
  - so need to use this script to run python
  ```
  #!/bin/bash

  # On OSX, two different types of Python builds exist: a regular build and
  # a framework build. In order to interact correctly with some GUI
  # frameworks, you need to use a framework build. Unfortuantly, on OSX
  # virtualenv always uses a regular build.
  #
  # The best known workaround, borrowed from the WX wiki, is to use the non-
  # virtualenv Python along with the PYTHONHOME environment variable.
  # See: http://matplotlib.org/faq/virtualenv_faq.html#osx

  if [ -z "$VIRTUAL_ENV" ]; then
      echo -e "\033[0;31mCould not find an activated virtualenv (required).\033[0m"
      exit 1
  fi

  # non-virtualenv Python executable to use
  PYTHON=/usr/local/bin/python3

  # run Python with the virtualenv set as Python's HOME
  PYTHONHOME=$VIRTUAL_ENV exec $PYTHON "$@"
  ```

Also note for python3 install pySerial and NOT serial with pip