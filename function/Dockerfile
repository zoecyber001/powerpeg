# Workpeg builds function images without internet access, so nothing here may be
# fetched from PyPI. The base image already carries the workpeg runtime (0.157.0),
# Python 3.12, the appuser, WORKDIR /app and the
# `workpeg function runtime --server` entrypoint.
#
# Third-party packages live in wheels/. Rebuild that bundle for the runtime's
# interpreter (cp312, linux x86_64) whenever requirements.txt changes:
#
#   pip download --only-binary=:all: --dest wheels --python-version 3.12 \
#     --implementation cp --abi cp312 --platform manylinux2014_x86_64 \
#     -r requirements.txt
FROM registry.gitlab.com/workpeg/workpeg-sdk/pegfn-base:0.157.0

COPY wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /app/requirements.txt

COPY app /app/app
