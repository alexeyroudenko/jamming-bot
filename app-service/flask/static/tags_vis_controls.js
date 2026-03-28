/**
 * Freeze animation + export PNG for canvas or Three.js renderer.
 * opts: { canvas?, getCanvas?, getRenderer?, onFreezeChange?(frozen: boolean) }
 */
(function (global) {
  'use strict';

  function getCanvas(opts) {
    if (opts.getCanvas) return opts.getCanvas();
    return opts.canvas || null;
  }

  function exportPng(opts) {
    var canvas = getCanvas(opts);
    if (!canvas) return;
    try {
      canvas.toBlob(function (blob) {
        if (!blob) return;
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'jamming-vis-' + Date.now() + '.png';
        a.click();
        setTimeout(function () {
          URL.revokeObjectURL(a.href);
        }, 2000);
      }, 'image/png');
    } catch (e) {
      console.error('Export failed', e);
    }
  }

  function exportThreeRenderer(renderer) {
    if (!renderer || !renderer.domElement) return;
    try {
      renderer.render(renderer.scene, renderer.camera);
      var data = renderer.domElement.toDataURL('image/png');
      var a = document.createElement('a');
      a.href = data;
      a.download = 'jamming-vis-' + Date.now() + '.png';
      a.click();
    } catch (e) {
      console.error('Export failed', e);
    }
  }

  global.TagsVisControls = {
    frozen: false,

    wire: function (opts) {
      var freezeBtn = document.getElementById('btn-freeze');
      var exportBtn = document.getElementById('btn-export');
      var self = this;

      if (freezeBtn) {
        freezeBtn.addEventListener('click', function () {
          self.frozen = !self.frozen;
          freezeBtn.textContent = self.frozen ? 'Unfreeze' : 'Freeze';
          freezeBtn.setAttribute('aria-pressed', self.frozen ? 'true' : 'false');
          if (opts.onFreezeChange) opts.onFreezeChange(self.frozen);
        });
      }

      if (exportBtn) {
        exportBtn.addEventListener('click', function () {
          if (typeof opts.onExport === 'function') {
            opts.onExport();
            return;
          }
          if (opts.getRenderer) {
            var r = opts.getRenderer();
            if (r && r.domElement) {
              exportThreeRenderer(r);
              return;
            }
          }
          exportPng(opts);
        });
      }
    },
  };
})(typeof window !== 'undefined' ? window : this);
