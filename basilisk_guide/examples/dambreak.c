// Collapse of a water column in a 1 m box (water and air, SI units).
#include "navier-stokes/centered.h"
#include "two-phase.h"
#include "navier-stokes/conserving.h"
#include "reduced.h"

#define LEVEL 7

int main()
{
  size (1.);                     // origin (0,0), box [0,1] x [0,1]
  init_grid (1 << LEVEL);
  rho1 = 1000., mu1 = 1e-3;      // water
  rho2 = 1.2,   mu2 = 1.8e-5;    // air
  G.y = -9.81;
  run();
}

// All four sides keep the default free-slip walls.

event init (t = 0)
{
  // water where x < 0.25 and y < 0.5: positive inside both half-planes
  fraction (f, min (0.25 - x, 0.5 - y));
}

// Position of the water front along the floor.
event front (t += 0.01; t <= 0.6)
{
  double xf = 0.;
  foreach (reduction(max:xf))
    if (y < 0.05 && f[] > 0.5 && x > xf)
      xf = x;
  static FILE * fp = NULL;
  if (!fp) {
    fp = fopen ("dambreak_front.dat", "w");
    fprintf (fp, "t xfront\n");
  }
  fprintf (fp, "%g %g\n", t, xf);
  fflush (fp);
}

event shape (t = {0, 0.2, 0.4, 0.6})
{
  char name[80];
  sprintf (name, "dambreak_facets_%g.dat", t);
  FILE * fp = fopen (name, "w");
  output_facets (f, fp);
  fclose (fp);
}

event logfile (i += 50)
  fprintf (stderr, "t = %g  i = %d  dt = %g  mgp = %d  cells = %ld\n",
           t, i, dt, mgp.i, grid->tn);

event adapt (i++)
  adapt_wavelet ({f, u}, (double[]){1e-3, 1e-2, 1e-2}, LEVEL, 4);
