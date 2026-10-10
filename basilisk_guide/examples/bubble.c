// Rising bubble (test case 1 of Hysing et al. 2009), simplified from
// $BASILISK/test/rising.c. Gravity points along -x.
#include "grid/multigrid.h"
#include "navier-stokes/centered.h"
#include "two-phase.h"
#include "tension.h"
#include "reduced.h"

// No-slip on the bottom (left) and top (right) ends; slip side walls (default).
u.t[right] = dirichlet(0);
u.t[left]  = dirichlet(0);

int main()
{
  dimensions (nx = 4);      // a 4 x 1 multigrid box ...
  size (2.);                // ... 2 long and 0.5 wide
  init_grid (1 << 7);       // 128 x 32 cells
  rho1 = 1000., mu1 = 10.;  // surrounding liquid (f = 1)
  rho2 = 100.,  mu2 = 1.;   // bubble (f = 0)
  f.sigma = 24.5;
  G.x = -0.98;              // gravity, via reduced.h
  Z.x = 1.;
  TOLERANCE = 1e-4;
  DT = 1.;
  run();
}

event init (t = 0)
{
  fraction (f, sq(x - 0.5) + sq(y) - sq(0.25));   // bubble of radius 0.25 at (0.5, 0)
}

// Bubble centroid and rise velocity, averaged over the bubble phase (1 - f).
event track (t += 0.01; t <= 3.)
{
  double vol = 0., xb = 0., vb = 0.;
  foreach (reduction(+:vol) reduction(+:xb) reduction(+:vb)) {
    double dvb = (1. - f[])*dv();
    vol += dvb;
    xb  += x*dvb;
    vb  += u.x[]*dvb;
  }
  static FILE * fp = NULL;
  if (!fp) {
    fp = fopen ("bubble_track.dat", "w");
    fprintf (fp, "t xc vc\n");
  }
  fprintf (fp, "%g %g %g\n", t, xb/vol, vb/vol);
  fflush (fp);
}

event shape (t = {0, 1, 2, 3})
{
  char name[80];
  sprintf (name, "bubble_facets_%g.dat", t);
  FILE * fp = fopen (name, "w");
  output_facets (f, fp);
  fclose (fp);
}

event logfile (i += 100)
  fprintf (stderr, "t = %g  i = %d  dt = %g  mgp = %d\n", t, i, dt, mgp.i);
