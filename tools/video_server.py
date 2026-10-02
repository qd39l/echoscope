"""Local UI for the real RTL simulator. Browser code contains no world model."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import json
from pathlib import Path


def serve(sim, port, backend):
    page = (Path(__file__).resolve().parents[1]/'sim/viewer.html').read_bytes()
    sim.reset()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path not in ('/','/index.html'):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self):
            # No cross-origin control; serve only a loopback session.
            origin=self.headers.get('Origin')
            if origin and origin != f'http://{self.headers.get("Host")}':
                self.send_error(403)
                return
            if self.path != '/frame':
                self.send_error(404)
                return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 1024:
                    raise ValueError('Invalid request length')
                data=json.loads(self.rfile.read(length))
                controls, address=int(data['controls']),int(data['address'])
                if not 0 <= controls <= 127 or not 0 <= address <= 31:
                    raise ValueError('Invalid controls or cell address')
                if data.get('reset'):
                    sim.reset(controls)
                frame=sim.next_frame(controls,address)
                image=BytesIO()
                frame.image().save(image,format='PNG')
                payload=image.getvalue()
                self.send_response(200)
                self.send_header('Content-Type','image/png')
                self.send_header('Content-Length',str(len(payload)))
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Sim-Cycles',str(sim.cycles))
                self.send_header('X-Sim-Backend',backend)
                self.end_headers()
                self.wfile.write(payload)
            except (ValueError,KeyError,json.JSONDecodeError) as error:
                self.send_error(400,str(error))
            except (AssertionError,RuntimeError,TimeoutError,BrokenPipeError) as error:
                # A timing failure must stop the preview, never show a repaired frame.
                self.send_error(500,str(error))

    server=HTTPServer(('127.0.0.1',port),Handler)
    print(f'RTL VGA viewer: http://127.0.0.1:{port} ({backend}, simulated 25 MHz)',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
