package com.solarsystem.model;

import com.solarsystem.utils.Constants;
import com.solarsystem.utils.Vector3D;

public class CelestialBody {
    private double mass;
    private double defaultMass;
    private double radius;
    private Vector3D position;
    private Vector3D speed;
    private Vector3D acceleration;
    private CelestialBody father;
    private boolean dynamic;
    private String name;
    private boolean black;
    private double volume;
    private int texture;
    private double spin;
    private double spinSpeed;
    private double tilt;

    public CelestialBody(double mass, double radius, double x, double y, double z, CelestialBody father, boolean dynamic, String name, boolean black, int texture, double spinSpeed, double tilt) {
        this.mass = mass;
        this.defaultMass = mass;
        this.radius = radius;
        this.position = new Vector3D(x, y, z);
        this.speed = new Vector3D(0.0, 0.0, 0.0);
        this.acceleration = new Vector3D(0.0, 0.0, 0.0);
        this.father = father;
        this.dynamic = dynamic;
        this.name = name;
        this.black = black;
        this.volume = 4 * Math.PI * radius * radius * radius / 3;
        this.texture = texture;
        this.spin = 0.0;
        this.spinSpeed = spinSpeed;
        this.tilt = tilt;

        if (father != null){
            Vector3D distVec = this.position.subtract(father.position);
            double r = distVec.magnitude();
            if (r > 0.0){
                double d = Math.pow(r * r + Constants.EPS * Constants.EPS, 1.5);
                double vTan = Math.sqrt(Constants.G * father.mass * r * r / d);

                Vector3D rHat = distVec.normalize();
                Vector3D up = new Vector3D(0.0, 0.0, 1.0);
                if (Math.abs(rHat.dotProduct(up)) > 0.99){
                    up.setY(1.0);
                    up.setZ(0.0);
                }

                Vector3D tan = up.crossProduct(rHat);

                Vector3D norm = tan.normalize();

                this.speed = father.speed.plus(norm.scale(vTan));
            }
        }
    }

    public void updatePosition(double dt){
        if (this.dynamic){
            this.speed.add(this.acceleration.scale(0.5 * dt));
            this.position.add(this.speed.scale(dt));
        }
    }

    public void updateSpeed(double dt){
        if (this.dynamic){
            this.speed.add(this.acceleration.scale(0.5 * dt));
        }
    }

    public void resetAcceleration(){
        this.acceleration.setX(0.0);
        this.acceleration.setY(0.0);
        this.acceleration.setZ(0.0);
    }

    public void absorb(CelestialBody other){
        this.mass += other.mass;
        this.volume += other.volume;
        this.radius = Math.pow((3.0 * this.volume) / (Math.PI * 4.0), 1.0 / 3.0);
    }

    // Getters

    public double getMass() {
        return mass;
    }

    public double getDefaultMass() {
        return defaultMass;
    }

    public double getRadius() {
        return radius;
    }

    public Vector3D getPosition() {
        return position;
    }

    public Vector3D getSpeed() {
        return speed;
    }

    public Vector3D getAcceleration() {
        return acceleration;
    }

    public CelestialBody getFather() {
        return father;
    }

    public boolean isDynamic() {
        return dynamic;
    }

    public String getName() {
        return name;
    }

    public boolean isBlack() {
        return black;
    }

    public double getVolume() {
        return volume;
    }

    public int getTexture() {
        return texture;
    }

    public double getSpin() {
        return spin;
    }

    public double getSpinSpeed() {
        return spinSpeed;
    }

    public double getTilt() {
        return tilt;
    }

    // Setters

    public void setMass(double mass) {
        this.mass = mass;
    }

    public void setDefaultMass(double defaultMass) {
        this.defaultMass = defaultMass;
    }

    public void setRadius(double radius) {
        this.radius = radius;
    }

    public void setPosition(Vector3D position) {
        this.position = position;
    }

    public void setSpeed(Vector3D speed) {
        this.speed = speed;
    }

    public void setAcceleration(Vector3D acceleration) {
        this.acceleration = acceleration;
    }

    public void setFather(CelestialBody father) {
        this.father = father;
    }

    public void setDynamic(boolean dynamic) {
        this.dynamic = dynamic;
    }

    public void setName(String name) {
        this.name = name;
    }

    public void setBlack(boolean black) {
        this.black = black;
    }

    public void setVolume(double volume) {
        this.volume = volume;
    }

    public void setTexture(int texture) {
        this.texture = texture;
    }

    public void setSpin(double spin) {
        this.spin = spin;
    }

    public void setSpinSpeed(double spinSpeed) {
        this.spinSpeed = spinSpeed;
    }

    public void setTilt(double tilt) {
        this.tilt = tilt;
    }
}
