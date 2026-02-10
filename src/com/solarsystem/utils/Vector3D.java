package com.solarsystem.utils;


public class Vector3D {
    private double x;
    private double y;
    private double z;

    public Vector3D(double x, double y, double z){
        this.x = x;
        this.y = y;
        this.z = z;
    }

    public void add(Vector3D other){
        this.x += other.x;
        this.y += other.y;
        this.z += other.z;
    }

    public Vector3D plus(Vector3D other) {
        return new Vector3D(this.x + other.x, this.y + other.y, this.z + other.z);
    }

    public Vector3D subtract(Vector3D other){
        return new Vector3D(this.x -= other.x, this.y -= other.y, this.z -= other.z);
    }

    public Vector3D scale(double scale){
        return new Vector3D(this.x * scale, this.y * scale, this.z * scale);
    }

    public double magnitude(){
        return Math.sqrt(x * x + y * y + z * z);
    }

    public double distanceTo(Vector3D other){
        double dx = this.x - other.x;
        double dy = this.x - other.y;
        double dz = this.z - other.z;
        return Math.sqrt(dx * dx + dy * dy + dz * dz);
    }

    public Vector3D normalize(){
        double mag = magnitude();
        if (mag == 0) return new Vector3D(0, 0, 0);

        return new Vector3D(x / mag, y / mag, z / mag);
    }

    public Vector3D crossProduct(Vector3D other){
        double cx = this.y * other.z - this.z * other.y;
        double cy = this.z * other.x - this.x * other.z;
        double cz = this.x * other.y - this.y * other.x;

        return new Vector3D(cx, cy, cz);
    }

    public double dotProduct(Vector3D other) {
        return this.x * other.x + this.y * other.y + this.z * other.z;
    }

    @Override
    public String toString() {
        return String.format("(%.2f, %.2f, %.2f)", x, y, z);
    }

    // Getters

    public double getX() {
        return x;
    }

    public double getY() {
        return y;
    }

    public double getZ() {
        return z;
    }

    // Setters

    public void setX(double x) {
        this.x = x;
    }

    public void setY(double y) {
        this.y = y;
    }

    public void setZ(double z) {
        this.z = z;
    }
}
