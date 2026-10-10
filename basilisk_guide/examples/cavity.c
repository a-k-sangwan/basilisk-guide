// Lid-driven cavity at Re = 1000 on a uniform 64 x 64 grid.
#include "grid/multigrid.h"
#include "navier-stokes/centered.h"

// No-slip walls, lid moving at u = 1. The normal components keep their
// default (zero), so only the tangential ones need setting.
u.t[top]    = dirichlet(1.);
u.t[bottom] = dirichlet(0.);
u.t[left]   = dirichlet(0.);
u.t[right]  = dirichlet(0.);
uf.n[left]  = 0.;
uf.n[right] = 0.;
uf.n[top]   = 0.;
uf.n[bottom] = 0.;

int main()
{
  origin (-0.5, -0.5);   // unit box centred on (0,0)
  init_grid (64);
  mu[] = {1e-3, 1e-3};   // constant viscosity: Re = U L / nu = 1000
  DT = 0.1;
  run();
}

scalar un[];             // u.x at the previous check, to detect steady state

event init (t = 0)
{
  foreach()
    un[] = u.x[];
}

static void write_results (void)
{
  FILE * fp = fopen ("cavity_profile.dat", "w");
  fprintf (fp, "y ux\n");
  for (double y = -0.495; y < 0.5; y += 0.01)   // stay inside the domain
    fprintf (fp, "%g %g\n", y, interpolate (u.x, 0., y));
  fclose (fp);
  scalar omega[];
  vorticity (u, omega);
  output_ppm (omega, file = "cavity_vorticity.png", n = 400,
              min = -5, max = 5, linear = true);
}

// Every 0.5 time units: log, and stop once the flow no longer changes.
event logfile (t += 0.5; t <= 60.)
{
  double du = change (u.x, un);
  fprintf (stderr, "t = %g  i = %d  du = %g  mgp = %d  mgu = %d\n",
           t, i, du, mgp.i, mgu.i);
  if ((i > 0 && du < 1e-4) || t >= 60.) {
    write_results();
    return 1;            // a non-zero return value ends the run
  }
}
