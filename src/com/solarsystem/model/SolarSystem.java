package com.solarsystem.model;

import com.solarsystem.utils.Constants;

import java.util.ArrayList;
import java.util.List;

public class SolarSystem {
    private List<CelestialBody> bodies;
    private List<CelestialBody> massiveBodies;

    public SolarSystem() {
        this.bodies = new ArrayList<>();
        this.massiveBodies = new ArrayList<>();
    }

    public void addBody(CelestialBody body){
        this.bodies.add(body);
        if (body.getMass() > Constants.MIN_MASSIVE){
            this.massiveBodies.add(body);
        }
    }

    public void removeBody(CelestialBody body){
        this.bodies.remove(body);
        this.massiveBodies.remove(body);
    }

    public void removeBodies(List<CelestialBody> bodies){
        for (CelestialBody body: bodies){
            this.bodies.remove(body);
            this.massiveBodies.remove(body);
        }
    }

    public List<CelestialBody> getBodies() {
        return bodies;
    }

    public List<CelestialBody> getMassiveBodies() {
        return massiveBodies;
    }
}
