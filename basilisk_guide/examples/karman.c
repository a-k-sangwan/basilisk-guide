// Flow past a cylinder at Re = 160: a Karman vortex street.
// Adapted from $BASILISK/examples/karman.c, with the drag coefficient added.
#include "embed.h"
#include "navier-stokes/centered.h"

double Reynolds = 160., D = 0.125, U0 = 1.;
int maxlevel = 9;
face vector muv[];

int main()
{
  L0 = 8.;
  origin (-0.5, -L0/2.);
  N = 512;
  mu = muv;
  run();
}

event properties (i++)
{
  foreach_face()
    muv.x[] = fm.x[]*D*U0/Reynolds;   // mu = U0 D / Re, times the open face fraction
}

// Inflow on the left, outflow on the right, slip walls top and bottom (default).
u.n[left]  = dirichlet(U0);
p[left]    = neumann(0.);
pf[left]   = neumann(0.);
u.n[right] = neumann(0.);
p[right]   = dirichlet(0.);
pf[right]  = dirichlet(0.);

// No-slip cylinder.
u.n[embed] = dirichlet(0.);
u.t[embed] = dirichlet(0.);

event init (t = 0)
{
  solid (cs, fs, sqrt(sq(x) + sq(y)) - D/2.);
  foreach()
    u.x[] = cs[] ? U0 : 0.;
}

// Drag and lift coefficients from the pressure and viscous forces.
event coefficients (t += 0.01)
{
  coord Fp, Fmu;
  embed_force (p, u, mu, &Fp, &Fmu);
  double q = 0.5*sq(U0)*D;   // rho = 1
  static FILE * fp = NULL;
  if (!fp) {
    fp = fopen ("karman_forces.dat", "w");
    fprintf (fp, "t Cd Cl\n");
  }
  fprintf (fp, "%g %g %g\n", t, (Fp.x + Fmu.x)/q, (Fp.y + Fmu.y)/q);
  fflush (fp);
}

event logfile (i += 50)
  fprintf (stderr, "t = %g  i = %d  dt = %g  mgp = %d  mgu = %d  cells = %ld\n",
           t, i, dt, mgp.i, mgu.i, grid->tn);

event snapshot (t = 15)
{
  scalar omega[], m[];
  vorticity (u, omega);
  foreach()
    m[] = cs[] - 0.5;          // mask out the solid
  output_ppm (omega, file = "karman_vorticity.png", n = 1024,
              box = {{-0.5,-0.5},{7.5,0.5}}, min = -10, max = 10,
              linear = true, mask = m);
}

event adapt (i++)
  adapt_wavelet ({cs,u}, (double[]){1e-2,3e-2,3e-2}, maxlevel, 4);
