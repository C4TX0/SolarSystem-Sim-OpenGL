package com.solarsystem.physics;

import com.solarsystem.model.CelestialBody;
import com.solarsystem.model.SolarSystem;
import com.solarsystem.utils.Constants;
import com.solarsystem.utils.Vector3D;

import java.util.ArrayList;
import java.util.List;

public class PhysicsEngine {
    public void calculateForces(SolarSystem system){
        for (CelestialBody body: system.getBodies()){
            if (!body.isDynamic()){
                body.setAcceleration(new Vector3D(0.0, 0.0, 0.0));
                continue;
            }
            Vector3D acceleration = new Vector3D(0.0, 0.0, 0.0);
            for (CelestialBody other: system.getMassiveBodies()){
                if (body == other){
                    continue;
                }
                Vector3D direction = other.getPosition().subtract(body.getPosition());
                double r2 = direction.dotProduct(direction) + Constants.EPS * Constants.EPS;
                double invR = 1.0 / Math.sqrt(r2);
                double invR3 = invR * invR * invR;
                acceleration.add(direction.scale(Constants.G * other.getMass() * invR3));
            }
            body.setAcceleration(acceleration);
        }
    }

    public void integrate(SolarSystem system, double dt){
        for (CelestialBody body: system.getBodies()){
            body.updatePosition(dt);
        }
        this.calculateForces(system);
        for (CelestialBody body: system.getBodies()){
            body.updateSpeed(dt);
        }
    }

    public void checkCollision(SolarSystem system) {
        List<CelestialBody> bodies = system.getBodies();
        List<CelestialBody> toRemove = new ArrayList<>();
        for (CelestialBody body : bodies) {
            if (toRemove.contains(body)) continue;
            for (CelestialBody other : bodies) {
                if (body == other) continue;
                if (toRemove.contains(other)) continue;
                if (body.getMass() <= Constants.MIN_MASSIVE && other.getMass() <= Constants.MIN_MASSIVE) {
                    continue;
                }
                double distance = body.getPosition().distanceTo(other.getPosition());
                double minDistance = body.getRadius() + other.getRadius();
                if (distance < minDistance) {
                    CelestialBody winner, loser;
                    if (body.getMass() >= other.getMass()) {
                        winner = body;
                        loser = other;
                    } else {
                        winner = other;
                        loser = body;
                    }
                    winner.absorb(loser);
                    if (!toRemove.contains(loser)) {
                        toRemove.add(loser);
                    }
                }
            }
        }
        bodies.removeAll(toRemove);
    }
}
